# -*- coding: utf-8 -*-
{
    'name': "tdt_cfe",

    'summary': u'Facturación electrónica Uruguay',

    'description': u'Facturación electrónica Uruguay',
    'author': "TDT Ventures",
    'website': "http://www.tdtconsultants.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'web',
        'base_vat',
        'account',
        'tdt_tc_bcu',
        'l10n_uy',
    ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/default_partner.xml',
        'data/taxes.xml',
        'data/payment_terms.xml',
        'data/dgi_tax_codes.xml',
        'data/resguardo_journal.xml',
        'views/cfe_encabezado.xml',
        'views/cfe.xml',
        #'views/cfe_resguardo.xml',
        'views/company.xml',
        'views/invoice.xml',
        'views/partner.xml',
        'views/taxes_view.xml',
        'views/payment_term_view.xml',
        'views/ejemplo_resguardo.xml',
        #'views/resguardo.xml',
    ],
    'external_dependencies':{
        'python':['xmltodict','qrcode']
    },
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
