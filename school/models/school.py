# See LICENSE file for full copyright and licensing details.

# import time
import re
import calendar
from datetime import datetime
from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import except_orm
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


EM = (r"[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$")


def emailvalidation(email):
    """Check valid email."""
    if email:
        email_regex = re.compile(EM)
        if not email_regex.match(email):
            raise ValidationError(_('''Cela ne semble pas être un e-mail valide.
             Veuillez saisir l'e-mail au format correct!'''))
        else:
            return True


class AcademicYear(models.Model):
    '''Defines an academic year.'''

    _name = "academic.year"
    _description = "Academic Year"
    _order = "sequence"

    sequence = fields.Integer('Séquence', required=True,
                              help="Ordre de séquence que vous voulez voir cette année.")
    name = fields.Char('Nom', required=True, help="Nom de l'année académique")
    code = fields.Char('Code', required=True, help="Code de l'année académique")
    date_start = fields.Date('Date de début', required=True,
                             help="Date de début de l'année académique")
    date_stop = fields.Date('Date de fin', required=True,
                            help="Date de fin de l'année académique")
    month_ids = fields.One2many('academic.month', 'year_id', 'Mois',
                                help="mois académiques associés")
    grade_id = fields.Many2one('grade.master', "Classe")
    current = fields.Boolean('Courant', help="Définir l'année en cours active")
    description = fields.Text('Description')

    @api.model
    def next_year(self, sequence):
        '''This method assign sequence to years'''
        year_id = self.search([('sequence', '>', sequence)], order='id',
                              limit=1)
        if year_id:
            return year_id.id
        return False

    def name_get(self):
        '''Method to display name and code'''
        return [(rec.id, ' [' + rec.code + ']' + rec.name) for rec in self]

    def generate_academicmonth(self):
        """Generate academic months."""
        interval = 1
        month_obj = self.env['academic.month']
        for data in self:
            ds = data.date_start
            while ds < data.date_stop:
                de = ds + relativedelta(months=interval, days=-1)
                if de > data.date_stop:
                    de = data.date_stop
                month_obj.create({
                    'name': ds.strftime('%B'),
                    'code': ds.strftime('%m/%Y'),
                    'date_start': ds.strftime('%Y-%m-%d'),
                    'date_stop': de.strftime('%Y-%m-%d'),
                    'year_id': data.id,
                })
                ds = ds + relativedelta(months=interval)
        return True

    @api.constrains('date_start', 'date_stop')
    def _check_academic_year(self):
        '''Method to check start date should be greater than end date
           also check that dates are not overlapped with existing academic
           year'''
        new_start_date = self.date_start
        new_stop_date = self.date_stop
        delta = new_stop_date - new_start_date
        if delta.days > 365 and not calendar.isleap(new_start_date.year):
            raise ValidationError(_('''Erreur! La durée de l'année académique
                                       est invalide.'''))
        if (self.date_stop and self.date_start and
                self.date_stop < self.date_start):
            raise ValidationError(_('''La date de début de l'année académique '
                                       doit être inférieur à la date de fin.'''))
        for old_ac in self.search([('id', 'not in', self.ids)]):
            # Check start date should be less than stop date
            if (old_ac.date_start <= self.date_start <= old_ac.date_stop or
                    old_ac.date_start <= self.date_stop <= old_ac.date_stop):
                raise ValidationError(_('''Erreur! Vous ne pouvez pas définir de chevauchement
                                           années universitaires.'''))

    @api.constrains('current')
    def check_current_year(self):
        check_year = self.search([('current', '=', True)])
        if len(check_year.ids) >= 2:
            raise ValidationError(_('''Erreur! Vous ne pouvez pas définir deux \
année active!'''))


class AcademicMonth(models.Model):
    '''Defining a month of an academic year.'''

    _name = "academic.month"
    _description = "Academic Month"
    _order = "date_start"

    name = fields.Char('Nom', required=True, help='Nom du mois académique')
    code = fields.Char('Code', required=True, help='Code du mois académique')
    date_start = fields.Date('Début de la période', required=True,
                             help='Début du mois académique')
    date_stop = fields.Date('Fin de période', required=True,
                            help='Fin du mois académique')
    year_id = fields.Many2one('academic.year', 'Année académique', required=True,
                              help="Année académique connexe ")
    description = fields.Text('Description')

    _sql_constraints = [
        ('month_unique', 'unique(date_start, date_stop, year_id)',
         'Le mois académique doit être unique!'),
    ]

    @api.constrains('date_start', 'date_stop')
    def _check_duration(self):
        '''Method to check duration of date'''
        if (self.date_stop and self.date_start and
                self.date_stop < self.date_start):
            raise ValidationError(_(''' La date de fin de période doit être postérieure à la date de début de période!'''))

    @api.constrains('year_id', 'date_start', 'date_stop')
    def _check_year_limit(self):
        '''Method to check year limit'''
        if self.year_id and self.date_start and self.date_stop:
            if (self.year_id.date_stop < self.date_stop or
                    self.year_id.date_stop < self.date_start or
                    self.year_id.date_start > self.date_start or
                    self.year_id.date_start > self.date_stop):
                raise ValidationError(_('''Mois invalides! Quelques mois se chevauchent
                                     ou la période de date n'est pas dans le champ d'application
                                     de l'année académique!'''))

    @api.constrains('date_start', 'date_stop')
    def check_months(self):
        """Check start date should be less than stop date."""
        for old_month in self.search([('id', 'not in', self.ids)]):
            if old_month.date_start <= \
                    self.date_start <= old_month.date_stop \
                    or old_month.date_start <= \
                    self.date_stop <= old_month.date_stop:
                raise ValidationError(_('''Erreur! Vous ne pouvez pas définir
                     mois qui se chevauchent!'''))


class StandardMedium(models.Model):
    ''' Defining a medium(ENGLISH, HINDI, GUJARATI) related to standard'''

    _name = "standard.medium"
    _description = "Moyen standard"
    _order = "sequence"

    sequence = fields.Integer('Séquence', required=True)
    name = fields.Char('Nom', required=True)
    code = fields.Char('Code', required=True)
    description = fields.Text('Description')


class StandardDivision(models.Model):
    '''Defining a division(A, B, C) related to standard'''

    _name = "standard.division"
    _description = "Division standard"
    _order = "sequence"

    sequence = fields.Integer('Séquence', required=True)
    name = fields.Char('Nom', required=True)
    code = fields.Char('Code', required=True)
    description = fields.Text('Description')


class StandardStandard(models.Model):
    '''Defining Standard Information.'''

    _name = 'standard.standard'
    _description = 'Standard Information'
    _order = "sequence"

    sequence = fields.Integer('Séquence', required=True)
    name = fields.Char('Nom', required=True)
    code = fields.Char('Code', required=True)
    description = fields.Text('Description')

    @api.model
    def next_standard(self, sequence):
        '''This method check sequence of standard'''
        stand_ids = self.search([('sequence', '>', sequence)], order='id',
                                limit=1)
        if stand_ids:
            return stand_ids.id
        return False


class SchoolStandard(models.Model):
    '''Defining a standard related to school.'''

    _name = 'school.standard'
    _description = 'Normes scolaires'
    _rec_name = "standard_id"

    @api.depends('standard_id', 'school_id', 'division_id', 'medium_id',
                 'school_id')
    def _compute_student(self):
        '''Compute student of done state'''
        student_obj = self.env['student.student']
        for rec in self:
            rec.student_ids = student_obj.\
                search([('standard_id', '=', rec.id),
                        ('school_id', '=', rec.school_id.id),
                        ('division_id', '=', rec.division_id.id),
                        ('medium_id', '=', rec.medium_id.id),
                        ('state', '=', 'done')])

    @api.onchange('standard_id', 'division_id')
    def onchange_combine(self):
        self.name = str(self.standard_id.name
                        ) + '-' + str(self.division_id.name)

    @api.depends('subject_ids')
    def _compute_subject(self):
        '''Method to compute subjects.'''
        for rec in self:
            rec.total_no_subjects = len(rec.subject_ids)

    @api.depends('student_ids')
    def _compute_total_student(self):
        for rec in self:
            rec.total_students = len(rec.student_ids)

    @api.depends("capacity", "total_students")
    def _compute_remain_seats(self):
        for rec in self:
            rec.remaining_seats = rec.capacity - rec.total_students

    school_id = fields.Many2one('school.school', 'École', required=True)
    standard_id = fields.Many2one('standard.standard', 'Norme',
                                  required=True)
    division_id = fields.Many2one('standard.division', 'Division',
                                  required=True)
    medium_id = fields.Many2one('standard.medium', 'Moyenne', required=True)
    subject_ids = fields.Many2many('subject.subject', 'subject_standards_rel',
                                   'subject_id', 'standard_id', 'Matière')
    user_id = fields.Many2one('school.teacher', 'Professeur de classe')
    student_ids = fields.One2many('student.student', 'standard_id',
                                  'Étudiant en classe',
                                  compute='_compute_student', store=True
                                  )
    color = fields.Integer('Index de couleur')
    cmp_id = fields.Many2one('res.company', 'Raison sociale',
                             related='school_id.company_id', store=True)
    syllabus_ids = fields.One2many('subject.syllabus', 'standard_id',
                                   'Syllabus')
    total_no_subjects = fields.Integer('Nombre total de sujets',
                                       compute="_compute_subject")
    name = fields.Char('Nom')
    capacity = fields.Integer("Nombre total de sièges")
    total_students = fields.Integer("Nombre total d'étudiants",
                                    compute="_compute_total_student",
                                    store=True)
    remaining_seats = fields.Integer("Places libres",
                                     compute="_compute_remain_seats",
                                     store=True)
    class_room_id = fields.Many2one('class.room', 'Numéro de chambre')

    @api.constrains('standard_id', 'division_id')
    def check_standard_unique(self):
        """Method to check unique standard."""
        standard_search = self.env['school.standard'
                                   ].search([('standard_id', '=',
                                              self.standard_id.id),
                                             ('division_id', '=',
                                              self.division_id.id),
                                             ('school_id', '=',
                                              self.school_id.id),
                                             ('id', 'not in', self.ids)])
        if standard_search:
            raise ValidationError(_('''La division et la classe doivent être uniques!'''
                                    ))
  
    def unlink(self):
        for rec in self:
            if rec.student_ids or rec.subject_ids or rec.syllabus_ids:
                raise ValidationError(_('''Vous ne pouvez pas supprimer cette norme
                 parce qu'il a une référence avec l'étudiant ou la matière ou
                 programme!'''))
        return super(SchoolStandard, self).unlink()

    @api.constrains('capacity')
    def check_seats(self):
        """Method to check seats."""
        if self.capacity <= 0:
            raise ValidationError(_('''Le nombre total de sièges doit être supérieur à
                 0!'''))

    def name_get(self):
        '''Method to display standard and division'''
        return [(rec.id, rec.standard_id.name + '[' + rec.division_id.name +
                 ']') for rec in self]


class SchoolSchool(models.Model):
    ''' Defining School Information'''

    _name = 'school.school'
    _description = "Information sur l'école"
    _rec_name = "com_name"

    @api.model
    def _lang_get(self):
        '''Method to get language'''
        languages = self.env['res.lang'].search([])
        return [(language.code, language.name) for language in languages]

    company_id = fields.Many2one('res.company', 'Entreprise',
                                 ondelete="cascade",
                                 required=True,
                                 delegate=True)
    com_name = fields.Char("Nom de l'école", related='company_id.name',
                           store=True)
    code = fields.Char('Code', required=True)
    standards = fields.One2many('school.standard', 'school_id',
                                'Normes')
    lang = fields.Selection(_lang_get, 'Langue',
                            help='''Si la langue sélectionnée est chargée dans le
                                 système, tous les documents relatifs à ce partenaire
                                 sera imprimé dans cette langue.
                                 Sinon, ce sera l'anglais.''')
    required_age = fields.Integer("Âge d'admission des étudiants requis", default=18)

    @api.model
    def create(self, vals):
        res = super(SchoolSchool, self).create(vals)
        main_company = self.env.ref('base.main_company')
        res.company_id.parent_id = main_company.id
        return res


class SubjectSubject(models.Model):
    '''Defining a subject '''
    _name = "subject.subject"
    _description = "Sujets"

    name = fields.Char('Nom', required=True)
    code = fields.Char('Code', required=True)
    maximum_marks = fields.Integer("Notes maximales")
    minimum_marks = fields.Integer("Notes minimales")
    weightage = fields.Integer("WeightAge")
    teacher_ids = fields.Many2many('school.teacher', 'subject_teacher_rel',
                                   'subject_id', 'teacher_id', 'Enseignants')
    standard_ids = fields.Many2many('standard.standard',
                                    string='Normes')
    standard_id = fields.Many2one('standard.standard', 'Classe')
    is_practical = fields.Boolean('Est pratique',
                                  help='Cochez ceci si le sujet est pratique.')
    elective_id = fields.Many2one('subject.elective')
    student_ids = fields.Many2many('student.student',
                                   'elective_subject_student_rel',
                                   'subject_id', 'student_id', 'Étudiants')


class SubjectSyllabus(models.Model):
    '''Defining a  syllabus'''
    _name = "subject.syllabus"
    _description = "Syllabus"
    _rec_name = "subject_id"

    standard_id = fields.Many2one('school.standard', 'Standard')
    subject_id = fields.Many2one('subject.subject', 'Matière')
    syllabus_doc = fields.Binary("Syllabus Doc",
                                 help="Joindre le Syllabus lié au sujet")


class SubjectElective(models.Model):
    ''' Defining Subject Elective '''
    _name = 'subject.elective'
    _description = "Matière optionnelle"

    name = fields.Char("Nom")
    subject_ids = fields.One2many('subject.subject', 'elective_id',
                                  'Sujets électifs')


class MotherTongue(models.Model):
    """Defining mother tongue."""

    _name = 'mother.toungue'
    _description = "Langue maternelle"

    name = fields.Char("Langue maternelle")


class StudentAward(models.Model):
    """Defining student award."""

    _name = 'student.award'
    _description = "Prix étudiants"

    award_list_id = fields.Many2one('student.student', 'Étudiant')
    name = fields.Char('Nom du prix')
    description = fields.Char('Description')


class AttendanceType(models.Model):
    """Defining attendance type."""

    _name = "attendance.type"
    _description = "Type d'école"

    name = fields.Char('Nom', required=True)
    code = fields.Char('Code', required=True)


class StudentDocument(models.Model):
    """Defining Student document."""
    _name = 'student.document'
    _description = "Document étudiant"
    _rec_name = "doc_type"

    doc_id = fields.Many2one('student.student', 'Etudiant')
    file_no = fields.Char('No de dossier', readonly="1", default=lambda obj:
                          obj.env['ir.sequence'].
                          next_by_code('student.document'))
    submited_date = fields.Date('Date de soumission')
    doc_type = fields.Many2one('document.type', 'Type de document', required=True)
    file_name = fields.Char('Nom de fichier',)
    return_date = fields.Date('Date de retour')
    new_datas = fields.Binary('Pièces jointes')


class DocumentType(models.Model):
    ''' Defining a Document Type(SSC,Leaving)'''
    _name = "document.type"
    _description = "Type de document"
    _rec_name = "doc_type"
    _order = "seq_no"

    seq_no = fields.Char('Séquence', readonly=True,
                         default=lambda self: _('New'))
    doc_type = fields.Char('Type de document', required=True)

    @api.model
    def create(self, vals):
        if vals.get('seq_no', _('New')) == _('New'):
            vals['seq_no'] = self.env['ir.sequence'
                                      ].next_by_code('document.type'
                                                     ) or _('New')
        return super(DocumentType, self).create(vals)


class StudentDescription(models.Model):
    ''' Defining a Student Description'''
    _name = 'student.description'
    _description = "Student Description"

    des_id = fields.Many2one('student.student', 'Étudiant Ref.')
    name = fields.Char('Nom')
    description = fields.Char('Description')


class StudentDescipline(models.Model):
    """Definign student dscipline."""

    _name = 'student.descipline'
    _description = "Discipline étudiant"

    student_id = fields.Many2one('student.student', 'Étudiant')
    teacher_id = fields.Many2one('school.teacher', 'Professeur')
    date = fields.Date('Date')
    class_id = fields.Many2one('standard.standard', 'Classe')
    note = fields.Text('Note')
    action_taken = fields.Text('Action prise')


class StudentHistory(models.Model):
    """Defining Student History."""

    _name = "student.history"
    _description = "Histoire des étudiants"

    student_id = fields.Many2one('student.student', 'Étudiant')
    academice_year_id = fields.Many2one('academic.year', 'Année académique',
                                        )
    standard_id = fields.Many2one('school.standard', 'Normes')
    percentage = fields.Float("Pourcentage", readonly=True)
    result = fields.Char('Résultat', readonly=True)


class StudentCertificate(models.Model):
    """Defining student certificate."""

    _name = "student.certificate"
    _description = "Certificat étudiant"

    student_id = fields.Many2one('student.student', 'Étudiant')
    description = fields.Char('Description')
    certi = fields.Binary('Certificat', required=True)


class StudentReference(models.Model):
    ''' Defining a student reference information '''

    _name = "student.reference"
    _description = "Référence de l'étudiant"

    reference_id = fields.Many2one('student.student', 'Etudiant')
    name = fields.Char('Prénom', required=True)
    middle = fields.Char('Deuxième nom', required=True)
    last = fields.Char('Nom', required=True)
    designation = fields.Char('Désignation', required=True)
    phone = fields.Char('Téléphone', required=True)
    gender = fields.Selection([('male', 'Mâle'), ('female', 'Femelle')],
                              'Gender')


class StudentPreviousSchool(models.Model):
    ''' Defining a student previous school information '''
    _name = "student.previous.school"
    _description = "École précédente de l'élève"

    previous_school_id = fields.Many2one('student.student', 'Etudiant')
    name = fields.Char('Nom', required=True)
    registration_no = fields.Char("N ° d'enregistrement.", required=True)
    admission_date = fields.Date("Date d'admission")
    exit_date = fields.Date('Date de sortie')
    course_id = fields.Many2one('standard.standard', 'Cours', required=True)
    add_sub = fields.One2many('academic.subject', 'add_sub_id', 'Ajouter des sujets')

    @api.constrains('admission_date', 'exit_date')
    def check_date(self):
        curr_dt = datetime.now()
        new_dt = datetime.strftime(curr_dt,
                                   DEFAULT_SERVER_DATE_FORMAT)
        if self.admission_date >= new_dt or self.exit_date >= new_dt:
            raise ValidationError(_('''Votre date d'admission et date de sortie
             devrait être inférieur à la date actuelle dans les détails de l'école précédente!'''))
        if self.admission_date > self.exit_date:
            raise ValidationError(_(''' La date d'admission doit être inférieure à
             date de sortie à l'école précédente!'''))


class AcademicSubject(models.Model):
    ''' Defining a student previous school information '''
    _name = "academic.subject"
    _description = "École précédente de l'élève"

    add_sub_id = fields.Many2one('student.previous.school', 'Ajouter des sujets',
                                 invisible=True)
    name = fields.Char('Nom', required=True)
    maximum_marks = fields.Integer("Marques maximales")
    minimum_marks = fields.Integer("Notes minimales")


class StudentFamilyContact(models.Model):
    ''' Defining a student emergency contact information '''
    _name = "student.family.contact"
    _description = "Contact famille étudiant"

    @api.depends('relation', 'stu_name')
    def _compute_get_name(self):
        for rec in self:
            if rec.stu_name:
                rec.relative_name = rec.stu_name.name
            else:
                rec.relative_name = rec.name

    family_contact_id = fields.Many2one('student.student', 'Réf étudiant.')
    rel_name = fields.Selection([('exist', "Lien vers l'étudiant existant"),
                                 ('new', 'Créer un nouveau nom relatif')],
                                'Étudiant lié', help="Sélectionnez un nom",
                                required=True)
    user_id = fields.Many2one('res.users', 'Utilisateur ID', ondelete="cascade")
    stu_name = fields.Many2one('student.student', 'Étudiant existant',
                               help="Sélectionnez un étudiant dans la liste existante")
    name = fields.Char('Relative Nom')
    relation = fields.Many2one('student.relation.master', 'Relation',
                               required=True)
    phone = fields.Char('Téléphone', required=True)
    email = fields.Char('E-Mail')
    relative_name = fields.Char(compute='_compute_get_name', string='Nom')


class StudentRelationMaster(models.Model):
    ''' Student Relation Information '''
    _name = "student.relation.master"
    _description = "Student Relation Master"

    name = fields.Char('Nom', required=True, help="Entrez le nom de la relation")
    seq_no = fields.Integer('Séquence')


class GradeMaster(models.Model):
    """Defining grade master."""

    _name = 'grade.master'
    _description = "Grade Master"

    name = fields.Char('Note', required=True)
    grade_ids = fields.One2many('grade.line', 'grade_id', 'Lignes de grade')


class GradeLine(models.Model):
    """Defining grade line."""

    _name = 'grade.line'
    _description = "Notes"
    _rec_name = 'grade'

    from_mark = fields.Integer('A partir de note', required=True,
                               help='La note commencera à partir de ces notes.')
    to_mark = fields.Integer('Terminera à note', required=True,
                             help='La note se terminera à cette note.')
    grade = fields.Char('Note', required=True, help="Note")
    sequence = fields.Integer('Séquence', help="Ordre de séquence de la note.")
    fail = fields.Boolean('Échouer', help="Si le champ d'échec est défini sur True, \
                                   cela vous permettra de définir la note comme échec.")
    grade_id = fields.Many2one("grade.master", 'Note Ref.')
    name = fields.Char('Nom')


class StudentNews(models.Model):
    """Defining studen news."""

    _name = 'student.news'
    _description = 'Student News'
    _rec_name = 'subject'
    _order = 'date asc'

    subject = fields.Char('Subject', required=True,
                          help="Sujet de l'actualité.")
    description = fields.Text('Description', help="Description")
    date = fields.Datetime("Date d'expiration", help="Date d'expiration de la nouvelle.")
    user_ids = fields.Many2many('res.users', 'user_news_rel', 'id', 'user_ids',
                                'Nouvelles des utilisateurs',
                                help='Nom à qui cette nouvelle est liée.')
    color = fields.Integer('Index coleur', default=0)

    @api.constrains("date")
    def checknews_dates(self):
        """Check news date."""
        new_date = datetime.now()
        if self.date < new_date:
            raise ValidationError(_('''Configurer la date d'expiration supérieure à \ la
date actuelle!'''))

    def news_update(self):
        '''Method to send email to student for news update'''
        emp_obj = self.env['hr.employee']
        obj_mail_server = self.env['ir.mail_server']
        user = self.env['res.users'].browse(self._context.get('uid'))
        # Check if out going mail configured
        mail_server_ids = obj_mail_server.search([])
        if not mail_server_ids:
            raise except_orm(_('Mail Error'),
                             _('''Aucun serveur de courrier sortant \
spécifié!'''))
        mail_server_record = mail_server_ids[0]
        email_list = []
        # Check email is defined in student
        for news in self:
            if news.user_ids and news.date:
                email_list = [news_user.email for news_user in news.user_ids
                              if news_user.email]
                if not email_list:
                    raise except_orm(_('User Email Configuration!'),
                                     _("E-mail introuvable chez les utilisateurs !"))
            # Check email is defined in user created from employee
            else:
                for employee in emp_obj.search([]):
                    if employee.work_email:
                        email_list.append(employee.work_email)
                    elif employee.user_id and employee.user_id.email:
                        email_list.append(employee.user_id.email)
                if not email_list:
                    raise except_orm(_('Email Configuration!'),
                                     _("Email not defined!"))
            news_date = news.date
            # Add company name while sending email
            company = user.company_id.name or ''
            body = """Hi,<br/><br/>
                    This is a news update from <b>%s</b> posted at %s<br/>
                    <br/> %s <br/><br/>
                    Thank you.""" % (company,
                                     news_date.strftime('%d-%m-%Y %H:%M:%S'),
                                     news.description or '')
            smtp_user = mail_server_record.smtp_user or False
            # Check if mail of outgoing server configured
            if not smtp_user:
                raise except_orm(_('Email Configuration '),
                                 _("Veuillez configurer le serveur de courrier sortant!"))
            notification = 'Notification de mise à jour des actualités.'
            # Configure email
            message = obj_mail_server.build_email(email_from=smtp_user,
                                                  email_to=email_list,
                                                  subject=notification,
                                                  body=body,
                                                  body_alternative=body,
                                                  reply_to=smtp_user,
                                                  subtype='html')
            # Send Email configured above with help of send mail method
            obj_mail_server.send_email(message=message,
                                       mail_server_id=mail_server_ids[0].id)
        return True


class StudentReminder(models.Model):
    """Defining student reminder."""

    _name = 'student.reminder'
    _description = "Rappel étudiant"

    @api.model
    def check_user(self):
        '''Method to get default value of logged in Student'''
        return self.env['student.student'].search([('user_id', '=',
                                                    self._uid)]).id

    stu_id = fields.Many2one('student.student', "Nom d'étudiant", required=True,
                             default=check_user)
    name = fields.Char('Titre')
    date = fields.Date('Date')
    description = fields.Text('Description')
    color = fields.Integer('Index couleur', default=0)


class StudentCast(models.Model):
    """Defining student cast."""

    _name = "student.cast"
    _description = "Cast étudiant"

    name = fields.Char("Nom", required=True)


class ClassRoom(models.Model):
    """Defining class room."""

    _name = "class.room"
    _description = "Salle"

    name = fields.Char("Nom")
    number = fields.Char("Numéro de la salle")


class Report(models.Model):
    _inherit = "ir.actions.report"

    def render_template(self, template, values=None):
        student_id = self.env['student.student'].\
            browse(self._context.get('student_id', False))
        if student_id and student_id.state == 'draft':
            raise ValidationError(_('''Vous ne pouvez pas imprimer le rapport pour
                 étudiant dans un état non confirmé!'''))
        return super(Report, self).render_template(template, values)
