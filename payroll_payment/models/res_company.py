from odoo import _, api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"
    
    account_debit_id = fields.Many2one(comodel_name='account.account', string='Cuenta Debito')
    account_credit_id = fields.Many2one(comodel_name='account.account', string='Cuenta Credito')
