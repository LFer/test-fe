# -*- coding: utf-8 -*-
{
    'name': "ras_trans_print_invoice",

    'summary': """
            Invoice reports customization for Ras Transport""",
    'description': """
            Invoice reports customization for Ras Transport""",
    'author': "TDT Consultants",
    'website': "http://www.tdtconsultants.com",

    # Categories can be used to filter modules in modules listing
    # for the full list
    'category': 'tdt',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['web_enterprise', 'tdt_cfe', 'account'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'data/data.xml',
        'views/invoice.xml',
        'templates/report_invoice.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'data/demo.xml',
    ],
    'license': 'OPL-1',
}
