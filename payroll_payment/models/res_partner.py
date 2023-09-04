from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'
    _description = 'Res Partner'

    is_payroll = fields.Boolean(string='Is Payroll', default=False)
