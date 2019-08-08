# -*- coding: utf-8 -*-
from odoo import models, fields

class dgi_tax_code(models.Model):
    _name = 'account.taxcode'
    name = fields.Char('Name', required="True")
    code = fields.Integer('Code', required="True")

class tax(models.Model):
    _inherit = 'account.tax'
    dgi_tax_code = fields.Many2one(
       'account.taxcode',
       'DGI tax code',
   )
