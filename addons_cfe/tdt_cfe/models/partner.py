# -*- coding: utf-8 -*-
from odoo import models, fields, api


class partner(models.Model):
    _inherit = 'res.partner'

    tipo_documento = fields.Selection([(2,'RUT'),(3, 'C.I'),(4, 'Otros'),(5,'Pasaporte'),(6,'DNI'),(7,'NIFE')], string='Tipo de Documento', default = 2)

    @api.multi
    def _get_uruguay(self):
        return self.env.ref('base.uy')

    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict', default = _get_uruguay)
    city = fields.Char(default = 'Montevideo')

    def tiene_documento_nacional(self):
        return self.tipo_documento == 3 or self.tipo_documento == 2

    def codigo_pais(self):
        return self.country_id.code if self.country_id.code else 'UY'
