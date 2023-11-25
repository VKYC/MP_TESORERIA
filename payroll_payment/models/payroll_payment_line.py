from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class PayrollPaymentLine(models.Model):
    _name = 'payroll.payment.line'
    _description = 'Payroll Payment Line'
    
    move_id = fields.Many2one('account.move', string='Factura')
    date = fields.Date(string='Fecha', related='move_id.date')
    currency_id = fields.Many2one('res.currency', string='Moneda', related='move_id.currency_id')
    amount_total = fields.Monetary(string='Total', currency_field='currency_id', related='move_id.amount_total')
    state = fields.Selection(string='Estado', related='move_id.state')
    mp_flujo_id = fields.Many2one(comodel_name="mp.flujo", related='move_id.mp_flujo_id', store=True, readonly=False)
    mp_grupo_flujo_ids = fields.Many2many(related="mp_flujo_id.grupo_flujo_ids")
    mp_grupo_flujo_id = fields.Many2one(comodel_name="mp.grupo.flujo", domain="[('id', 'in', mp_grupo_flujo_ids)]", related='move_id.mp_grupo_flujo_id', store=True, readonly=False)
    payroll_payment_id = fields.Many2one('payroll.payment', string='Nómina')
    to_check = fields.Boolean(string='A revisar', related='move_id.to_check')
    
    _sql_constraints = [
        ("move_unique", "unique(move_id)", "La factura ya se encuentra en una nómina."),
    ]
    
    @api.onchange("mp_flujo_id")
    def _onchange_mp_flujo_id(self):
        for register_id in self:
            register_id.mp_grupo_flujo_id = self.env['mp.grupo.flujo']
    
    def unlink(self):
        for record in self:
            if record.payroll_payment_id and record.payroll_payment_id.state != 'draft':
                raise ValidationError(_('No se puede eliminar una factura que ya ha sido enviada.'))
            record.move_id.payroll_payment_id = False
        return super(PayrollPaymentLine, self).unlink()
    
    def action_review(self):
        self.ensure_one()
        context = {
            "default_move_id": self.move_id.id,
        }
        self.move_id.to_check = True
        context.update(self.env.context)
        view_id = self.env.ref("payroll_payment.account_move_observation_view_form").id
        return {
            "type": "ir.actions.act_window",
            "name": "Oservación",
            "res_model": "account.move.observation",
            "view_mode": "form",
            "views": [(view_id, "form")],
            "target": "new",
            "context": context,
        }