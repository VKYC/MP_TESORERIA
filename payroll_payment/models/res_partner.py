from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'
    _description = 'Res Partner'

    is_payroll = fields.Boolean(string='Es nómina', default=False)
    blocked_for_payments = fields.Boolean(string='Bloqueado para pagos', default=False)
    blocked_for_purchases = fields.Boolean(string='Bloqueado para compras', default=False) 
    subject_discount = fields.Boolean(string='Sujeto a descuento', default=False)
    percentage_discount = fields.Float(string='Porcentaje de descuento', default=0.0)
    retention_account_id = fields.Many2one(comodel_name="account.account", string="Cuenta de retención")