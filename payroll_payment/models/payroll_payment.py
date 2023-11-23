from odoo import _, api, fields, models
import io
import xlsxwriter
import base64
from odoo.exceptions import ValidationError
class PayrollPayment(models.Model):
    _name = 'payroll.payment'
    _description = 'Payroll Payment'
    
    name = fields.Char(string='Código', required=True, default=lambda self: _('New'), readonly=True)
    date = fields.Date('Fecha')
    currency_id = fields.Many2one('res.currency', string='Moneda', default=lambda self: self.env.company.currency_id)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('send', 'Enviada'), 
        ('approved', 'Aprobado'), 
        ('generation_payroll', 'Generación de nómina'), 
        ('done', 'Procesado')
        ], string='Estado', default='draft')
    number_of_invoices = fields.Integer('Cantidad de facturas', compute='_compute_number_of_invoices')
    bank_id = fields.Many2one('res.partner.bank', string='Banco')
    # move_ids = fields.One2many('account.move', 'payroll_payment_id', string='Facturas')
    line_ids = fields.One2many('payroll.payment.line', 'payroll_payment_id', string='Facturas')
    budget = fields.Monetary(string='Presupuesto', currency_field='currency_id')
    amount_total =  fields.Monetary(string='Total', currency_field='currency_id', compute='_compute_amount_total')
    payroll_xlsx = fields.Binary(string='Nómina XLSX')
    payroll_xlsx_filename = fields.Char(string='Nombre del archivo XLSX')
    
    @api.depends('line_ids', 'line_ids.amount_total')
    def _compute_amount_total(self):
        for record in self:
            record.amount_total = sum(record.line_ids.mapped('amount_total'))
    
    @api.depends('line_ids')
    def _compute_number_of_invoices(self):
        for record in self:
            record.number_of_invoices = len(record.line_ids)
            
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('payroll.payment') or _('New')
        result = super(PayrollPayment, self).create(vals)
        return result
    
    def convert_to_send(self):
        if self.amount_total > self.budget:
            raise ValidationError(_('El monto total de las facturas es mayor al presupuesto.'))
        if not self.line_ids:
            raise ValidationError(_('Debe seleccionar al menos una factura.'))
        if self.line_ids and not all(self.line_ids.mapped(lambda r: bool(r.mp_flujo_id) and bool(r.mp_grupo_flujo_id))):
            raise ValidationError(_('Debe seleccionar un grupo y flujo para todas las facturas.'))
        if self.line_ids and all(self.line_ids.mapped(lambda r: bool(r.mp_flujo_id) and bool(r.mp_grupo_flujo_id))) and self.amount_total <= self.budget:
            self.state = 'send'
        
    def generate_payroll_xlsx(self):
        # Create an in-memory output file for the new workbook.
        output = io.BytesIO()
        # Create a workbook and add
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Nómina')
        # Add a bold format to use to highlight cells.
        bold = workbook.add_format({'bold': True})
        # Write some data headers.
        worksheet.write('A1', 'Fecha', bold)
        worksheet.write('B1', 'Código', bold)
        worksheet.write('C1', 'Nombre', bold)
        worksheet.write('D1', 'Cédula', bold)
        worksheet.write('E1', 'Cuenta', bold)
        worksheet.write('F1', 'Banco', bold)
        worksheet.write('G1', 'Monto', bold)
        # Start from the first cell below the headers.
        row = 1
        col = 0
        # Iterate over the data and write it out row by row.
        for line in self.line_ids:
            worksheet.write(row, col, line.date)
            worksheet.write(row, col + 1, line.move_id.name)
            worksheet.write(row, col + 2, line.move_id.partner_id.name)
            worksheet.write(row, col + 3, line.move_id.partner_id.vat)
            worksheet.write(row, col + 4, line.move_id.partner_id.bank_ids[0].acc_number)
            worksheet.write(row, col + 5, line.move_id.partner_id.bank_ids[0].bank_id.name)
            worksheet.write(row, col + 6, line.amount_total)
            row += 1
        workbook.close()
        output.seek(0)
        # construct the file name
        filename = f'{self.name}-{self.bank_id.acc_number}'.replace(' ', '_').replace('-', '_') + '.xlsx'
        # Get the value of the BytesIO buffer and put it in the response
        self.payroll_xlsx = base64.b64encode(output.getvalue())
        # self.payroll_xlsx = output.read().encode('base64')
        self.payroll_xlsx_filename = filename
        
    def convert_approved(self):
        self.state = 'approved'
    
    def print_payroll(self):
        # construir excel
        self.generate_payroll_xlsx()
        download =  {
            'type': 'ir.actions.act_url',
            'url': '/web/content/payroll.payment/%s/payroll_xlsx/%s?download=true' % (self.id, self.payroll_xlsx_filename),
            'target': 'self',
        }
        
        # download =  {
        #     'type': 'binary',
        #     'data': '/web/content/payroll.payment/%s/payroll_xlsx/%s?download=true' % (self.id, self.payroll_xlsx_filename),
        #     'target': 'self',
        # }
        
        self.state = 'generation_payroll'
        return download
    
    def convert_to_done(self):
        self.state = 'done'
    
    def convert_to_draft(self):
        self.state = 'draft'