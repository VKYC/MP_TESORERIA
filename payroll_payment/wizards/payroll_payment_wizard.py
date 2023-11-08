from odoo import _, api, fields, models

class PayrollPaymentWizard(models.Model):
    _name = 'payroll.payment.wizard'
    _description = 'Payroll Payment Wizard'
    
    date = fields.Date('Fecha', related='payroll_payment_id.date')
    bank_id = fields.Many2one('res.partner.bank', string='Banco', related='payroll_payment_id.bank_id')
    payroll_payment_id = fields.Many2one('payroll.payment', string='Nómina')
    
    def process_payroll(self):
        move_ids = self.env.context.get('active_ids', [])
        moves = self.env['account.move'].browse(move_ids)
        moves_to_process = moves.filtered(
            lambda move: move.for_payroll
            and move.payment_state == 'not_paid' 
            and move.currency_id == self.payroll_payment_id.currency_id 
            and len(move.partner_id.bank_ids) > 0 
            and not move.partner_id.blocked_for_payments 
            and move.partner_id.is_payroll
            )
        # if self.payroll_payment_id.state == 'draft':
        moves_to_process.write({
            # 'for_payroll': True,
            'payroll_payment_id': self.payroll_payment_id.id
                    })
        if self.payroll_payment_id.amount_total > self.payroll_payment_id.budget:
            warning = {}
            warning['warning'] = {
            'title': 'Advertencia!',
            'message': f'Usted a excedido el presupuesto de la nómina {self.payroll_payment_id.name}.'
            }
            return warning