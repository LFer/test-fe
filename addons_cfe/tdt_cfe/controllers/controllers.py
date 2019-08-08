# -*- coding: utf-8 -*-
from odoo import http

# class Cfe(http.Controller):
#     @http.route('/cfe/cfe/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/cfe/cfe/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('cfe.listing', {
#             'root': '/cfe/cfe',
#             'objects': http.request.env['cfe.cfe'].search([]),
#         })

#     @http.route('/cfe/cfe/objects/<model("cfe.cfe"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('cfe.object', {
#             'object': obj
#         })