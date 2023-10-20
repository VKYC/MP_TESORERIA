from odoo import _, api, fields, models

class PayrollPaymentWizard(models.Model):
    _name = 'payroll.payment.wizard'
    _description = 'Payroll Payment Wizard'
    
    date = fields.Date('Fecha')
    bank_id = fields.Many2one('res.partner.bank', string='Banco')
    payroll_payment_id = fields.Many2one('payroll.payment', string='Nómina')
    
    def to_payroll(self):
        move_ids = self.env.context.get('active_ids', [])
        moves = self.env['account.move'].browse(move_ids)
        moves.write({'for_payroll': True})
        return True