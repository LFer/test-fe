# -*- coding: utf-8 -*-
from odoo import api,fields,models
from odoo.exceptions import UserError
from ..currency_rate import update_service_BCU
import requests
import datetime
import urllib
import json


class ResCompany(models.Model):
    _inherit = 'res.company'

    currency_provider = fields.Selection([('bcu','Banco Central del Uruguay')], default="bcu")

    @api.multi
    def update_currency_rates(self):
        for company in self:
            if company.currency_provider == 'bcu' and company._update_currency_bcu():
                return True 
            else:
                return super(ResCompany,self).update_currency_rates()
                
    #se necesitarían configurar los iso codes de cada moneda que se quiera traer

    @api.one
    def _update_currency_bcu(self):
        Currency = self.env['res.currency']
        CurrencyRate = self.env['res.currency.rate']
        
        # la moneda debe ser UYU, si no hay que configurar el rate en proporción (ej: ver currency_rate_live)
        try:
            currency_array=['USD', 'ARS', 'BRL', 'UYR', 'PYG',]
            cotdict = update_service_BCU.get_updated_currency(currency_array, None)

        except:
            raise Warning('Hubo un problema con la actualización de las cotizaciones')
            return False
        
        CurrencyRate = self.env['res.currency.rate']
        USD = self.env.ref("base.USD")
        ARS = self.env.ref("base.ARS")
        BRL = self.env.ref("base.BRL")
        PYG = self.env.ref("base.PYG")
        UR = self.env.ref("tdt_tc_bcu.BCU_UR")
        curr_usd = CurrencyRate.search(['&', ('name', '=', fields.Datetime.now()), ('currency_id', '=', USD.id)])
        curr_asd= CurrencyRate.search(['&', ('name', '=', fields.Datetime.now()), ('currency_id', '=', ARS.id)])
        curr_brl = CurrencyRate.search(['&', ('name', '=', fields.Datetime.now()), ('currency_id', '=', BRL.id)])
        curr_uyr = CurrencyRate.search(['&', ('name', '=', fields.Datetime.now()), ('currency_id', '=', UR.id)])
        curr_pyg = CurrencyRate.search(['&', ('name', '=', fields.Datetime.now()), ('currency_id', '=', PYG.id)])
        for company in self:
            if not company.currency_id == self.env.ref("base.UYU"):
                raise UserError(u'La moneda base de la compañía %s es incorrecta - se debe utilizar moneda base UYU para usar el bcu para sincronizar monedas.' % company.name)

            if curr_usd:
                CurrencyRate.write({'rate': cotdict['USD'],})
            else:
                CurrencyRate.create({'currency_id': USD.id, 'rate': cotdict['USD'], 'name': fields.Datetime.now(), 'company_id': company.id})

            if curr_asd:
                CurrencyRate.write({'rate': cotdict['ARS'],})
            else:
                CurrencyRate.create({'currency_id': ARS.id, 'rate': cotdict['ARS'], 'name': fields.Datetime.now(), 'company_id': company.id})

            if curr_brl:
                CurrencyRate.write({'rate': cotdict['BRL'],})
            else: CurrencyRate.create({'currency_id': BRL.id, 'rate': cotdict['BRL'], 'name': fields.Datetime.now(), 'company_id': company.id})
            if curr_uyr:
                CurrencyRate.write({'rate': cotdict['UYR'],})
            else:
                CurrencyRate.create({'currency_id': UR.id, 'rate': cotdict['UYR'], 'name': fields.Datetime.now(), 'company_id': company.id})

            if curr_pyg:
                CurrencyRate.write({'rate': cotdict['PYG'],})
            else:
                CurrencyRate.create({'currency_id': PYG.id, 'rate': cotdict['PYG'], 'name': fields.Datetime.now(), 'company_id': company.id})
                

        try:
            currency_array=['UYI',]
            year = datetime.datetime.now().year - 1
            fecha = datetime.datetime(year, 12, 31)
            cotdict = update_service_BCU.get_updated_currency(currency_array, fecha)

        except:
            raise Warning('Hubo un problema con la actualización de la unidad indexada')
            return False

        UI = self.env.ref("tdt_tc_bcu.BCU_UI")
        curr_uyi = CurrencyRate.search(['&', ('name', '=', fecha), ('currency_id', '=', UI.id)])
        for company in self:
            if curr_uyi:
                CurrencyRate.write({'rate': cotdict['UYI'],})
            else:
                CurrencyRate.create({'currency_id': UI.id, 'rate': cotdict['UYI'], 'name': fecha, 'company_id': company.id})
