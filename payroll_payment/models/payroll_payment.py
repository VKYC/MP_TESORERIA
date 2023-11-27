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
    partner_bank_id = fields.Many2one('res.partner.bank', string='Banco')
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
            
    def format_template_xlsx_bci(self, workbook):
        worksheet = workbook.add_worksheet('Nómina')
        # Add a bold format to use to highlight cells.
        bold = workbook.add_format({'bold': True})
        # Write some data headers.
        worksheet.write('A1', 'Nº Cuenta de Cargo', bold)
        worksheet.write('B1', 'Nº Cuenta de Destino', bold)
        worksheet.write('C1', 'Banco Destino', bold)
        worksheet.write('D1', 'Rut Benefeciario', bold)
        worksheet.write('E1', 'Dig Verif. Benefeciario', bold)
        worksheet.write('F1', 'Nombre Benefeciario', bold)
        worksheet.write('G1', 'Monto Transferencia', bold)
        worksheet.write('H1', 'Nº Factura Boleta', bold)
        worksheet.write('I1', 'Nº Orden de Compra', bold)
        worksheet.write('J1', 'Tipo de pago', bold)
        worksheet.write('K1', 'Mensaje Destinatario', bold)
        worksheet.write('L1', 'Email Destinatario', bold)
        worksheet.write('M1', 'Cuenta Destino inscrita como', bold)
        
        # Start from the first cell below the headers.
        row = 1
        col = 0
        # Iterate over the data and write it out row by row.
        for line in self.line_ids:
            worksheet.write(row, col, self.partner_bank_id.acc_number or '')
            worksheet.write(row, col + 1, line.move_id.partner_bank_id.acc_number or '')
            worksheet.write(row, col + 2, line.move_id.partner_bank_id.bank_id.payroll_code or '')
            worksheet.write(row, col + 3, line.move_id.partner_id.vat or '')
            worksheet.write(row, col + 4, line.move_id.partner_id.vat and line.move_id.partner_id.vat[-1] or '')
            worksheet.write(row, col + 5, line.move_id.partner_id.name or '')
            worksheet.write(row, col + 6, line.amount_total)
            worksheet.write(row, col + 7, line.move_id.name or '')
            worksheet.write(row, col + 8, line.move_id.ref or '')
            worksheet.write(row, col + 9, 'OTRO *')
            worksheet.write(row, col + 10, 'PAGO FINIQUITO *')
            worksheet.write(row, col + 11, line.move_id.partner_id.email or '')
            worksheet.write(row, col + 12, line.move_id.partner_id.name or '')
            row += 1
        workbook.close()
        
    def format_template_xlsx_itau(self, workbook):
        worksheet = workbook.add_worksheet('Nómina')
        # Add a bold format to use to highlight cells.
        bold = workbook.add_format({'bold': True})
        # Write some data headers.
        worksheet.write('A3', 'Rut Empresa', bold)
        worksheet.write('A4', 'Cantidad de Pagos', bold)
        worksheet.write('A5', 'Monto Total de Pagos', bold)
        worksheet.write('A6', 'Tipo de Producto', bold)
        worksheet.write('A7', 'Tipo de Servicio', bold)
        worksheet.write('A8', 'Nº Cuenta Cargo', bold)
        worksheet.write('A9', 'Glosa Cartola Origen', bold)
        worksheet.write('A10', 'Glosa Cartola Destino', bold)
        ############
        worksheet.write('B3', self.env.company.vat or '')
        worksheet.write('B4', len(self.line_ids))
        worksheet.write('B5', self.amount_total)
        worksheet.write('B6', 'Proveedores')
        worksheet.write('B7', 'PAGO_DE_PROVEEDORES')
        worksheet.write('B8', self.partner_bank_id.acc_number or '')
        worksheet.write('B9', 'TRASPASO A BCI')
        worksheet.write('B10', 'TRASPASO DESDE ITAU')
        ############
        worksheet.write('A12', 'Rut Beneficiario', bold)
        worksheet.write('B12', 'Nombre Benefeciario', bold)
        worksheet.write('C12', 'Monto', bold)
        worksheet.write('D12', 'Medio de Pago', bold)
        worksheet.write('E12', 'Código Banco', bold)
        worksheet.write('F12', 'Tipo de Cuenta', bold)
        worksheet.write('G12', 'Número de Cuenta', bold)
        worksheet.write('H12', 'Email', bold)
        worksheet.write('I12', 'Referencia Cliente', bold)
        worksheet.write('J12', 'Glosa Cartola Origen', bold)
        worksheet.write('K12', 'Glosa Cartola Destino', bold)
        worksheet.write('L12', 'Detalle de Pago', bold)
        # Start from the first cell below the headers.
        row = 12
        col = 0
        # Iterate over the data and write it out row by row.
        for line in self.line_ids:
            worksheet.write(row, col, line.move_id.partner_id.vat or '')
            worksheet.write(row, col + 1, line.move_id.partner_id.name or '')
            worksheet.write(row, col + 2, line.amount_total)
            worksheet.write(row, col + 3, 'Abono en cuenta *')
            worksheet.write(row, col + 4, line.move_id.partner_bank_id.bank_id.payroll_code or '')
            worksheet.write(row, col + 5, 'Cuenta corriente *')
            worksheet.write(row, col + 6, line.move_id.partner_bank_id.acc_number or '')
            worksheet.write(row, col + 7, line.move_id.partner_id.email or '')
            worksheet.write(row, col + 8, 'TRASPASO DESDE ITAU A BCI')
            worksheet.write(row, col + 9, 'TRASPASO A BCI')
            worksheet.write(row, col + 10, 'TRASPASO ENTRE CUENTAS ITAU A BCI')
            row += 1
        workbook.close()
        
    def format_template_xlsx_scotiabank(self, workbook):
        worksheet = workbook.add_worksheet('Nómina')
        # Add a bold format to use to highlight cells.
        bold = workbook.add_format({'bold': True})
        # Write some data headers.
        worksheet.write('A1', 'Rut Proveedor Beneficiario', bold)
        worksheet.write('B1', 'Nombre/Razón Social Beneficiario', bold)
        worksheet.write('C1', 'Tipo Documento', bold)
        worksheet.write('D1', 'Nº Referencia/Documento', bold)
        worksheet.write('E1', 'Monto Descuento', bold)
        worksheet.write('F1', 'Subtotal', bold)
        worksheet.write('G1', 'Forma Pago', bold)
        worksheet.write('H1', 'Nº Cuenta de Abono', bold)
        worksheet.write('I1', 'Banco Destino', bold)
        worksheet.write('J1', 'Cód. Suc', bold)
        worksheet.write('K1', 'Email Aviso', bold)
        worksheet.write('L1', 'Mensaje Aviso', bold)
        # Start from the first cell below the headers.
        row = 1
        col = 0
        # Iterate over the data and write it out row by row.
        for line in self.line_ids:
            worksheet.write(row, col, line.move_id.partner_id.vat or '')
            worksheet.write(row, col + 1, line.move_id.partner_id.name or '')
            worksheet.write(row, col + 2, '*')
            worksheet.write(row, col + 3, line.move_id.name or '')
            worksheet.write(row, col + 4, '*')
            worksheet.write(row, col + 5, '*')
            worksheet.write(row, col + 6, '*')
            worksheet.write(row, col + 7, line.move_id.partner_bank_id.acc_number or '')
            worksheet.write(row, col + 8, line.move_id.partner_bank_id.bank_id.name or '')
            worksheet.write(row, col + 9, '*')
            worksheet.write(row, col + 10, line.move_id.partner_id.email or '')
            worksheet.write(row, col + 11, '*')
            row += 1
        workbook.close()
        
    def generate_payroll_xlsx(self):
        # Create an in-memory output file for the new workbook.
        output = io.BytesIO()
        # Create a workbook and add
        workbook = xlsxwriter.Workbook(output)
        # Modifica el excel según el banco seleccionado
        if self.partner_bank_id.bank_id.format_template_xlsx:
            try:
                getattr(self, f'format_template_xlsx_{self.partner_bank_id.bank_id.format_template_xlsx}')(workbook)
            except Exception as e:
                raise ValidationError(_(e))
        else:
            raise ValidationError(_('No existe una plantilla para el banco seleccionado.'))
        output.seek(0)
        # construct the file name
        filename = f'{self.name}-{self.partner_bank_id.acc_number}'.replace(' ', '_').replace('-', '_') + '.xlsx'
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
        self.state = 'generation_payroll'
        return download
    
    def convert_to_done(self):
        self.state = 'done'
    
    def convert_to_draft(self):
        self.state = 'draft'
