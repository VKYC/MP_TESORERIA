from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = 'account.move'
    _description = 'Account Move'
    
    for_payroll = fields.Boolean(string='Para nómina', default=False)
    payroll_payment_id = fields.Many2one('payroll.payment', string='Nómina')
    mp_flujo_id = fields.Many2one(comodel_name="mp.flujo")
    mp_grupo_flujo_ids = fields.Many2many(related="mp_flujo_id.grupo_flujo_ids")
    mp_grupo_flujo_id = fields.Many2one(comodel_name="mp.grupo.flujo", domain="[('id', 'in', mp_grupo_flujo_ids)]")
    observation = fields.Text(string='Observación')
    observation_state = fields.Selection([('observed', 'Observado'), ('without_observation', 'Sin observación')]  ,string='Estado de la observación', compute='_compute_observation_state', store=True)
    start_date_retention = fields.Date(string='Fecha de inicio de retención', related='invoice_date')
    end_date_retention = fields.Date(string='Fecha de fin de retención')
    percentage_discount = fields.Float(string='Porcentaje de descuento', default=0.0, related='partner_id.percentage_discount')
    retention_amount = fields.Monetary(string='Monto de retención', compute='_compute_retention_amount', store=True, currency='currency_id')
    
    @api.depends('amount_total', 'percentage_discount')
    def _compute_retention_amount(self):
        for record in self:
            record.retention_amount = record.amount_total * record.percentage_discount / 100
    
    @api.depends('observation')
    def _compute_observation_state(self):
        for record in self:
            if record.observation:
                record.observation_state = 'observed'
            else:
                record.observation_state = 'without_observation'
    
    def to_payroll(self):
        move_ids = self.env.context.get('active_ids', [])
        moves = self.env['account.move'].browse(move_ids)
        moves_to_process = moves.filtered(lambda move: move.payment_state == 'not_paid' and move.partner_bank_id and not move.partner_id.blocked_for_payments and move.partner_id.is_payroll)
        moves_to_process.write({
            'for_payroll': True
            })
        return True
    
    @api.constrains('for_payroll')
    def _constrains_for_payroll(self):
        for record in self:
            if not record.for_payroll and record.payroll_payment_id and record.payroll_payment_id.state != 'draft':
                raise ValidationError(_('No se puede desmarcar una factura que ya ha sido enviada en nómina.'))
    
    
    @api.onchange('for_payroll')
    def _onchange_for_payroll(self):
        if not self.for_payroll and self.payroll_payment_id:
            if self.payroll_payment_id.state == 'draft':
                self.payroll_payment_id = False
        if self.for_payroll:
            if self.partner_id.blocked_for_payments:
                raise ValidationError(_('El proveedor se encuentra bloqueado para pagos.'))
            if not self.partner_id.is_payroll:
                raise ValidationError(_('El proveedor no es de nómina.'))
            if not self.partner_bank_id:
                raise ValidationError(_('La factura no tiene un banco destinatario asociado.'))
            if self.payment_state != 'not_paid':
                raise ValidationError(_('La factura ya ha sido pagada.'))

    @api.onchange("mp_flujo_id")
    def _onchange_mp_flujo_id(self):
        for register_id in self:
            register_id.mp_grupo_flujo_id = self.env['mp.grupo.flujo']

    def write(self, vals):
        if 'payroll_payment_id' in vals:
            for record in self:
                # if record.payroll_payment_id and record.payroll_payment_id.state != 'draft':
                if not self.user_has_groups('base.group_system') and record.payroll_payment_id and record.payroll_payment_id.state != 'draft':
                    raise ValidationError(_('No se puede cambiar la nómina de una factura que ya ha sido enviada.'))
                else:
                    line = record.payroll_payment_id.line_ids.filtered(lambda line: line.move_id.id == record.id)
                    if vals.get('payroll_payment_id') == False and line.exists():
                        super(AccountMove, record).write(vals)
                        line.unlink()
                    if vals.get('payroll_payment_id'):
                        self.env['payroll.payment.line'].create({
                            'move_id': record.id,
                            'payroll_payment_id': vals.get('payroll_payment_id'),
                        })
        return super(AccountMove, self).write(vals)
    
    @api.onchange('for_payroll')
    def _onchange_to_payroll(self):
        if self.for_payroll and self.partner_id.blocked_for_payments:
            raise ValidationError(_('El proveedor se encuentra bloqueado para pagos.'))

    def action_register_payment(self):
        for record in self:
            if record.partner_id.blocked_for_payments:
                raise ValidationError(_(f'{record.partner_id.name} se encuentra bloqueado para pagos.'))
            if record.to_check:
                raise ValidationError(_(f'{record.name} se encuentra en estado a revisar.'))
        return super(AccountMove, self).action_register_payment()

    # * RETENCIONES

    def _recompute_dynamic_lines(self, recompute_all_taxes=False, recompute_tax_base_amount=False):
        super(AccountMove, self)._recompute_dynamic_lines(recompute_all_taxes, recompute_tax_base_amount)
        if self.partner_id and self.partner_id.subject_discount:
            self.add_line_detraction()

    @api.onchange('retention_amount', 'percentage_discount', 'currency_id', 'invoice_line_ids')
    def onchange_retention_percent(self):
        for record in self:
            if record != record._origin:
                retention_account_id = self.partner_id.retention_account_id
                merc = record.line_ids.filtered(lambda line: line.exclude_from_invoice_tab and line.account_id == retention_account_id)
                if merc:
                    record.line_ids -= merc
                record._onchange_invoice_line_ids()

    def add_line_detraction(self):
        if not self.partner_id.retention_account_id:
            raise UserError('El proveedor seleccionado esta sujeto a descuento y no tiene una cuenta para pago de retenciones. Por favor, configurar cuenta.')

        retention_account_id = self.partner_id.retention_account_id
        line_credit = self.line_ids.filtered(lambda line: line.exclude_from_invoice_tab and line.account_id != retention_account_id and line.credit > 0)
        if self.state == 'draft' and self.line_ids and self.move_type == 'in_invoice' and self.retention_amount and line_credit:
            merc = self.line_ids.filtered(lambda line: line.exclude_from_invoice_tab and line.account_id == retention_account_id)
            if len(merc) > 1:
                raise UserError('Hay más de un apunte contable con la cuenta de pago de detracciones.')

            balance = self.retention_amount
            amount_currency = -1 * self.company_currency_id._convert(balance, self.currency_id, self.company_id, fields.Date.today())
            
            if not merc:
                values = {
                    'account_id': retention_account_id.id,
                    'balance': balance,
                    'debit': 0.0,
                    'credit': balance,
                    'amount_currency': amount_currency,
                    'price_unit': -1 * balance,
                    'exclude_from_invoice_tab': True,
                    'move_id': self.id,
                    'currency_id': self.currency_id.id
                }
                self.env['account.move.line'].new(values)
            else:
                merc.balance = balance
                merc.credit = balance
                merc.currency_id = self.currency_id.id

            if line_credit:
                line_credit.credit -= balance
                line_credit.amount_currency -= amount_currency
                line_credit.price_unit += balance
                line_credit._onchange_credit()
                line_credit._get_fields_onchange_balance()

            # Only synchronize one2many in onchange.
            if self != self._origin:
                self.invoice_line_ids = self.line_ids.filtered(lambda line: not line.exclude_from_invoice_tab)

    @api.depends('l10n_latam_document_type_id')
    def _compute_name(self):
        for move_id in self:
            if not move_id.l10n_latam_document_number:
                super(AccountMove, move_id)._compute_name()
            else:
                move_id.name = move_id.name
