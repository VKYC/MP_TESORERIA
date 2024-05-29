from odoo import _, api, fields, models
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta


class ForeignCurrencyCentralization(models.Model):
    _name = 'foreign.currency.centralization'
    _description = 'Foreign Currency Centralization'

    account_account_ids = fields.Many2many(comodel_name='account.account', string='Account')
    month = fields.Selection(selection=[
        ('01', 'January'),
        ('02', 'February'),
        ('03', 'March'),
        ('04', 'April'),
        ('05', 'May'),
        ('06', 'June'),
        ('07', 'July'),
        ('08', 'August'),
        ('09', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December')
    ], string='Month', required=True)
    year = fields.Selection(
        [(str(num), str(num)) for num in reversed(range((datetime.now().year) - 2, (datetime.now().year) + 5))],
        string='Year', required=True)
    currency_ids = fields.Many2many(comodel_name='res.currency', string='Currency',
                                    domain=lambda self: [('id', '!=', self.env.company.currency_id.id),
                                                         ('active', '=', True)])
    company_id = fields.Many2one(comodel_name='res.company', string='Company',
                                 default=lambda self: self.env.company)

    @api.onchange('currency_ids')
    def onchange_currency_ids(self):
        self.account_account_ids = False

    def create_records(self):
        for record in self:
            for account in record.account_account_ids:
                self.env['foreign.currency.centralization.line'].create({
                    'account_account_id': account.id,
                    'date': fields.Date.today(),
                    'rate': self.env['res.currency']._get_conversion_rate(account.currency_id,
                                                                          self.env.company.currency_id,
                                                                          self.env.company, fields.Date.today()),
                    'from_currency_id': account.currency_id.id,
                    'to_currency_id': self.env.company.currency_id.id,
                    'amount_total': self.env['res.currency']._convert(self.get_amount_total_move_lines(account),
                                                                      account.currency_id, self.env.company.currency_id,
                                                                      self.env.company, fields.Date.today())
                })

    def get_amount_total_move_lines(self, account):
        date_from = date(int(self.year), int(self.month), 1)
        date_to = date_from + relativedelta(months=1)
        move_lines = self.env['account.move.line'].search(
            [('account_id', '=', account.id), ('date', '>=', date_from), ('date', '<', date_to),
             ('move_id.state', '=', 'posted'), ('exclude_from_invoice_tab', '=', False)])
        amount_total = sum(move_lines.mapped('amount_currency'))
        return amount_total
