from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class AccountMove(models.Model):
    _inherit = 'account.move'
    _description = 'Account Move'
    
    for_payroll = fields.Boolean(string='Para nómina', default=False)
    payroll_payment_id = fields.Many2one('payroll.payment', string='Nómina')
    
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
            # else:
            #     raise ValidationError(_('No se puede desmarcar una factura que ya ha sido enviada en nómina.'))