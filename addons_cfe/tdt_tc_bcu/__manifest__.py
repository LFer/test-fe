# -*- coding: utf-8 -*-
{
    'name': "Tipo de cambio por BCU",

    'summary': u"""
        Módulo para traer el tipo de cambio legalmente válido del BCU para Uruguay""",

    'description': """
        Agrega al cron del sistema el tipo de cambio del BCU para facturar con el
        tipo de cambio correcto
    """,

    'author': "TDT Consultants",
    'website': "http://www.tdtconsultants.com",

    # Categories can be used to filter modules in modules listing
    'category': 'tdt',
    'version': '0.1',
    'depends': ['currency_rate_live','tdt_l10n_uy_departamentos'],

    # always loaded
    'data': [
        'views/views.xml',
        'data/data.xml',
    ],
    'license': 'OPL-1',
}
