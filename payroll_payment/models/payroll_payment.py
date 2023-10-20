from odoo import _, api, fields, models

class PayrollPayment(models.Model):
    _name = 'payroll.payment'
    _description = 'Payroll Payment'
    
    name = fields.Char('Código')
    date = fields.Date('Fecha')
    currency_id = fields.Many2one('res.currency', string='Moneda', default=lambda self: self.env.company.currency_id)
    state = fields.Selection([('draft', 'Borrador'), ('send', 'Enviada'), ('done', 'Procesado')], string='Estado', default='draft')
    number_of_invoices = fields.Integer('Cantidad de facturas', compute='_compute_number_of_invoices')
    bank_id = fields.Many2one('res.partner.bank', string='Banco')
    move_ids = fields.One2many('account.move', 'payroll_payment_id', string='Facturas')
    
    @api.depends('move_ids')
    def _compute_number_of_invoices(self):
        for record in self:
            record.number_of_invoices = len(record.move_ids)