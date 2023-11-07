{
    'name': 'Payroll Payment',
    'version': '1.0',
    'description': '',
    'summary': '',
    'author': 'Jhon Jairo Rojas Ortiz',
    'website': '',
    'license': 'LGPL-3',
    'category': '',
    'depends': [
        'account', 'base'
    ],
    'data': [
        'data/ir_sequence.xml',
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'views/account_move_views.xml',
        'views/payroll_payment_views.xml',
        'wizards/payroll_payment_wizard_views.xml',
    ],
    'demo': [

    ],
    'auto_install': False,
    'application': False,
    'assets': {

    }
}
