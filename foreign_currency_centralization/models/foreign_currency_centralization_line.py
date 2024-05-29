from odoo import _, api, fields, models


class ForeignCurrencyCentralizationLine(models.Model):
    _name = 'foreign.currency.centralization.line'
    _description = 'Foreign Currency Centralization Line'

    account_account_id = fields.Many2one('account.account', string='Account', required=True)
    date = fields.Date(string='Date', required=True)
    rate = fields.Float(string='Rate', required=True)
    from_currency_id = fields.Many2one(comodel_name='res.currency', string='From Currency', required=True)
    to_currency_id = fields.Many2one(comodel_name='res.currency', string='To Currency', required=True)
    amount_total = fields.Monetary(string='Amount Total', currency_field='to_currency_id', required=True)

    _sql_constraints = [
        ("date_unique", "unique(account_account_id, date, rate)", "The date must be unique!"),
    ]
