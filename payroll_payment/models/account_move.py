from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

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
    
    # @api.onchange('payroll_payment_id')
    # def _onchange_payroll_payment_id(self):
    #     pass
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
        if self.partner_id.blocked_for_payments:
            raise ValidationError(_('El proveedor se encuentra bloqueado para pagos.'))
        if self.to_check:
            raise ValidationError(_('La factura se encuentra en estado a revisar.'))
        return super(AccountMove, self).action_register_payment()

    @api.depends('l10n_latam_document_type_id')
    def _compute_name(self):
        if not self.l10n_latam_document_number:
            super(AccountMove, self)._compute_name()
        else:
            self.name = self.name
