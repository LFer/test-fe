# -*- coding: utf-8 -*-
from odoo import models, fields, api
class invoice(models.Model):
    _inherit = 'account.invoice'
    #Campos para la impresión de factura
    rt_service_id = fields.Many2one('rt.service','Service', ondelete='cascade', copy=False)
    print_output_reference = fields.Boolean('Output Reference', help="ID: referencia_de_salida")
    print_origin_destiny_grouped = fields.Boolean('Origin and Destiny Groups', help="ID: origen_destino_agrup")
    print_cont_grouped = fields.Boolean('Containers Groups', help="ID: contenedores_agrup")
    print_dmc_grouped = fields.Boolean('DUA, MIC, CRT Groups', help="ID: dua_mic_crt_agrup")
    print_invoice_ref = fields.Boolean('Reference', help="ID: referencia", default=True)
    print_date_start = fields.Boolean('Travel Date', help="ID: fecha_viaje")
    print_ms_in_out = fields.Boolean('No. MS', help="ID: ms_entrada and ms_salida")
    print_mic = fields.Boolean('No. MIC', help="ID: mic")
    print_crt = fields.Boolean('No. CRT', help="ID: crt")
    print_consignee = fields.Boolean('Consignee', help="ID: consignatario")
    print_bl = fields.Boolean('B/L', help="ID: bl")
    print_hours = fields.Boolean('Hours', help="ID: horas")
    print_journals = fields.Boolean('Journals', help="ID: journales")
    print_origin_destiny_city = fields.Boolean('Origin and Destiny City', help="ID: ciudad_origen and ciudad_destino")
    print_origin_destiny_deposit = fields.Boolean('Origin and Destiny Deposit/Address', help="ID: deposito_origen and deposito_destino")
    print_origin_destiny = fields.Boolean('Origin and Destiny', help="ID: origen and destino")
    print_container_number = fields.Boolean('No. Container', help="ID: numero_contenedor")
    print_container_size = fields.Boolean('Container Size', help="ID: tamano_contenedor")
    print_booking = fields.Boolean('No. Booking', help="ID: booking")
    print_purchase_order = fields.Boolean('Purchase Order', help="ID: orden_compra")
    print_gex = fields.Boolean('No. GEX', help="ID: gex")
    print_sender = fields.Boolean('Sender', help="ID: remito")
    print_dua = fields.Boolean('DUA',help="ID: dua")
    print_packages = fields.Boolean('Packages', help="ID: bultos")
    print_kg = fields.Boolean('Kilogram', help="ID: kg")
    print_volume = fields.Boolean('Volume', help="ID: volumen")
    print_extra_info = fields.Boolean('Extra Info', help="Others informations that the user need include in the invoice report.")

    def get_lines(self):
        for record in self:
            inv_lns = self.env['account.invoice.line']
            lines = inv_lns.search([('invoice_id', '=', record.id)])
            return lines 

    def get_amount_taxed_by_22(self):
        iva22_id = self.env['account.tax.group'].search([('name', '=', 'IVA 22%')]).id
        if not iva22_id:
            raise Warning('IVA 22% tax group not found')
            return False
        for record in self:
            lines = record.get_lines()
            amount = 0
            for l in lines:
                for t in l.invoice_line_tax_ids:
                    if t.tax_group_id.id == iva22_id:
                        amount = amount + l.price_subtotal
            return amount

    def get_amount_taxed_by_10(self):
        iva10_id = self.env['account.tax.group'].search([('name', '=', 'IVA 10%')]).id
        if not iva10_id:
            raise Warning('IVA 10% tax group not found')
            return False
        for record in self:
            lines = record.get_lines()
            amount = 0
            for l in lines:
                for t in l.invoice_line_tax_ids:
                    if t.tax_group_id.id == iva10_id:
                        amount = amount + l.price_subtotal
            return amount
