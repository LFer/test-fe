# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ResCompany(models.Model):
    _inherit = 'res.company'

    factura_electronicamente = fields.Boolean(u"Factura Electrónicamente")
    url_ucfe = fields.Char("URL UCFE")
    codigo_comercio = fields.Char(u"Código Comercio")
    codigo_terminal = fields.Char(u"Código Terminal")
    email_pdfs = fields.Char(u"Email Receptor de PDFs")
    usuario_ucfe = fields.Char(u'Usuario ucfe')
    pass_ucfe = fields.Char(u'Pass ucfe')
    codigo_dgi_sucursal = fields.Char(u'Código sucursal DGI')
    nombre_fantasia = fields.Char('Nombre Fantasía')
