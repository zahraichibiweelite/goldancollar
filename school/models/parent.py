# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class ParentRelation(models.Model):
    '''Defining a Parent relation with child.'''

    _name = "parent.relation"
    _description = "Informations sur la relation parent-enfant"

    name = fields.Char("Nom de la relation", required=True)


class SchoolParent(models.Model):
    '''Defining a Teacher information.'''

    _name = 'school.parent'
    _description = 'Information sur les parents'

    @api.onchange('student_id')
    def onchange_student_id(self):
        """Onchange Method for Student."""
        self.standard_id = [(6, 0, [])]
        self.stand_id = [(6, 0, [])]
        standard_ids = [student.standard_id.id
                        for student in self.student_id]
        if standard_ids:
            stand_ids = [student.standard_id.standard_id.id
                         for student in self.student_id]
            self.standard_id = [(6, 0, standard_ids)]
            self.stand_id = [(6, 0, stand_ids)]

    partner_id = fields.Many2one('res.partner', "Identifiant d'utilisateur", ondelete="cascade",
                                 delegate=True, required=True)
    relation_id = fields.Many2one('parent.relation', "Relation avec l'enfant")
    student_id = fields.Many2many('student.student', 'students_parents_rel',
                                  'students_parent_id', 'student_id',
                                  'Enfants')
    standard_id = fields.Many2many('school.standard',
                                   'school_standard_parent_rel',
                                   'class_parent_id', 'class_id',
                                   'Classe académique')
    stand_id = fields.Many2many('standard.standard',
                                'standard_standard_parent_rel',
                                'standard_parent_id', 'standard_id',
                                'Norme académique')
    teacher_id = fields.Many2one('school.teacher', 'Professeur',
                                 related="standard_id.user_id", store=True)

    @api.model
    def create(self, vals):
        parent_id = super(SchoolParent, self).create(vals)
        parent_grp_id = self.env.ref('school.group_school_parent')
        emp_grp = self.env.ref('base.group_user')
        parent_group_ids = [emp_grp.id, parent_grp_id.id]
        if vals.get('parent_create_mng'):
            return parent_id
        user_vals = {'name': parent_id.name,
                     'login': parent_id.email,
                     'email': parent_id.email,
                     'partner_id': parent_id.partner_id.id,
                     'groups_id': [(6, 0, parent_group_ids)]
                     }
        self.env['res.users'].create(user_vals)
        return parent_id

    @api.onchange('state_id')
    def onchange_state(self):
        """Onchange Method for State."""
        self.country_id = False
        if self.state_id:
            self.country_id = self.state_id.country_id.id
