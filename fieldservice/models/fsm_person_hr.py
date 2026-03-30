from odoo import api, fields, models


class FSMPerson(models.Model):
    _inherit = 'fsm.person'

    employee_id = fields.Many2one('hr.employee', string='Employee')

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.name = self.employee_id.name
            self.phone = self.employee_id.work_phone
            self.mobile = self.employee_id.mobile_phone
            self.email = self.employee_id.work_email