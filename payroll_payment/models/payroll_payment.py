from odoo import _, api, fields, models

class PayrollPayment(models.Model):
    _name = 'payroll.payment'
    _description = 'Payroll Payment'
    
    name = fields.Char(string='Código', required=True, default=lambda self: _('New'), readonly=True)
    date = fields.Date('Fecha')
    currency_id = fields.Many2one('res.currency', string='Moneda', default=lambda self: self.env.company.currency_id)
    state = fields.Selection([('draft', 'Borrador'), ('send', 'Enviada'), ('done', 'Procesado')], string='Estado', default='draft')
    number_of_invoices = fields.Integer('Cantidad de facturas', compute='_compute_number_of_invoices')
    bank_id = fields.Many2one('res.partner.bank', string='Banco')
    move_ids = fields.One2many('account.move', 'payroll_payment_id', string='Facturas')
    budget = fields.Monetary(string='Presupuesto', currency_field='currency_id')
    amount_total =  fields.Monetary(string='Total', currency_field='currency_id', compute='_compute_amount_total')
    
    @api.depends('move_ids', 'move_ids.amount_total')
    def _compute_amount_total(self):
        for record in self:
            record.amount_total = sum(record.move_ids.mapped('amount_total'))
    
    @api.depends('move_ids')
    def _compute_number_of_invoices(self):
        for record in self:
            record.number_of_invoices = len(record.move_ids)
            
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('payroll.payment') or _('New')
        result = super(PayrollPayment, self).create(vals)
        return result
    
    def convert_to_send(self):
        self.state = 'send'
    
    def convert_to_done(self):
        self.state = 'done'
    
    def convert_to_draft(self):
        self.state = 'draft'