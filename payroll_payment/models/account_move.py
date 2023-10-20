from odoo import _, api, fields, models

class AccountMove(models.Model):
    _inherit = 'account.move'
    _description = 'Account Move'
    
    for_payroll = fields.Boolean(string='Para nómina', default=False)
    payroll_payment_id = fields.Many2one('payroll.payment', string='Nómina')