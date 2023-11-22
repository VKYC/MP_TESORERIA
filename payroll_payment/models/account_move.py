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
                if record.payroll_payment_id.state != 'draft':
                    raise ValidationError(_('No se puede cambiar la nómina de una factura que ya ha sido enviada.'))
                else:
                    line = record.payroll_payment_id.line_ids.filtered(lambda line: line.move_id.id == record.id)
                    if line.exists():
                        line.unlink()
                    if vals.get('payroll_payment_id'):
                        self.env['payroll.payment.line'].create({
                            'move_id': record.id,
                            'payroll_payment_id': vals.get('payroll_payment_id'),
                        })
        return super(AccountMove, self).write(vals)