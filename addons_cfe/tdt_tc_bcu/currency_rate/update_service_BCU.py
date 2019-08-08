# -*- coding: utf-8 -*-

import logging
from suds.client import Client
import ssl
import datetime

# para que funcione con python 2.7.9+
if hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context

_logger = logging.getLogger(__name__)

supported_currency_array = [
        'AED', 'AFN', 'ALL', 'AMD', 'ANG', 'AOA', 'ARS', 'AUD', 'AWG', 'AZN',
        'BAM', 'BBD', 'BDT', 'BGN', 'BHD', 'BIF', 'BMD', 'BND', 'BOB', 'BRL',
        'BSD', 'BTN', 'BWP', 'BYR', 'BZD', 'CAD', 'CDF', 'CHF', 'CLP', 'CNY',
        'COP', 'CRC', 'CUP', 'CVE', 'CYP', 'CZK', 'DJF', 'DKK', 'DOP', 'DZD',
        'EEK', 'EGP', 'ERN', 'ETB', 'EUR', 'FJD', 'FKP', 'GBP', 'GEL', 'GGP',
        'GHS', 'GIP', 'GMD', 'GNF', 'GTQ', 'GYD', 'HKD', 'HNL', 'HRK', 'HTG',
        'HUF', 'IDR', 'ILS', 'IMP', 'INR', 'IQD', 'IRR', 'ISK', 'JEP', 'JMD',
        'JOD', 'JPY', 'KES', 'KGS', 'KHR', 'KMF', 'KPW', 'KRW', 'KWD', 'KYD',
        'KZT', 'LAK', 'LBP', 'LKR', 'LRD', 'LSL', 'LTL', 'LVL', 'LYD', 'MAD',
        'MDL', 'MGA', 'MKD', 'MMK', 'MNT', 'MOP', 'MRO', 'MTL', 'MUR', 'MVR',
        'MWK', 'MXN', 'MYR', 'MZN', 'NAD', 'NGN', 'NIO', 'NOK', 'NPR', 'NZD',
        'OMR', 'PAB', 'PEN', 'PGK', 'PHP', 'PKR', 'PLN', 'PYG', 'QAR', 'RON',
        'RSD', 'RUB', 'RWF', 'SAR', 'SBD', 'SCR', 'SDG', 'SEK', 'SGD', 'SHP',
        'SLL', 'SOS', 'SPL', 'SRD', 'STD', 'SVC', 'SYP', 'SZL', 'THB', 'TJS',
        'TMM', 'TND', 'TOP', 'TRY', 'TTD', 'TVD', 'TWD', 'TZS', 'UAH', 'UGX',
        'USD', 'UYU', 'UZS', 'VEB', 'VEF', 'VND', 'VUV', 'WST', 'XAF', 'XAG',
        'XAU', 'XCD', 'XDR', 'XOF', 'XPD', 'XPF', 'XPT', 'YER', 'ZAR', 'ZMK',
        'ZWD', 'UYI', 'UYR'
    ]

codigo_ISO_BCU = {'AUD': '0105',
         'ARS': '0501',
         'BRL': '1001',
         'EUR': '1111',
         'CLF': '1300',
         'NZD': '1490',
         'ZAR': '1620',
         'DKK': '1800',
         'USD': '2225',
         'CAD': '2309',
         'GBP': '2700',
         'JPY': '3600',
         'PEN': '4000',
         'CNY': '4150',
         'MNX': '4200',
         'HUF': '4300',
         'TRY': '4400',
         'NOK': '4600',
         'PYG': '4800',
         'ISK': '4900',
         'HKD': '5100',
         'KRW': '5300',
         'RUB': '5400',
         'COP': '5500',
         'MYR': '5600',
         'INR': '5700',
         'SEK': '5800',
         'CHF': '5900',
         'VEF': '6200',
         'UYI': '9800',
         'UYR': '9900',
         }    # se toma de la tabla de cotizaciones interbancarias, en UYU

codigo_BCU_ISO = {
    '0105': 'AUD',
    '0501': 'ARS',     # se toma de la tabla de cotizaciones interbancarias, en UYU
    '1001': 'BRL',     # se toma de la tabla de cotizaciones interbancarias, en UYU
    '1111': 'EUR',
    '1300': 'CLF', '1490': 'NZD', '1620': 'ZAR', '1800': 'DKK',
    '2225': 'USD',     # se toma de la tabla de cotizaciones interbancarias, en UYU
    '2309': 'CAD', '2700': 'GBP', '3600': 'JPY', '4000': 'PEN',
    '4150': 'CNY', '4200': 'MXN', '4300': 'HUF', '4400': 'TRY',
    '4600': 'NOK', '4800': 'PYG', '4900': 'ISK', '5100': 'HKD',
    '5300': 'KRW', '5400': 'RUB', '5500': 'COP', '5600': 'MYR',
    '5700': 'INR', '5800': 'SEK', '5900': 'CHF', '6200': 'VEF',
    '9800': 'UYI', '9900': 'UYR',
}

def validate_cur(currency):
        """Validate if the currency to update is supported"""
        if currency not in supported_currency_array:
            raise Warning('Unsuported Currency') 

def _get_rate_date ():
    """Obtención de la fecha de cierre (la válida) para la cotización
    :return: fecha en formato aaaa-mm-dd
    """
    url = 'https://cotizaciones.bcu.gub.uy/wscotizaciones/servlet/awsultimocierre?WSDL'
    client = Client(url)
    try:
        result = client.service.Execute()
        fecha = result['Fecha']
    except:
        _logger.error(client)
    return fecha

def _get_currency_list(currency_array):
    """A partir de la la lista de códigos ISO de las monedas crea una lista de códigos de monedas en el formato
    esperado por el servicio awsbcucotizaciones
    """
    list = []
    for currency in currency_array:
        if currency in codigo_ISO_BCU:
            list.append(codigo_ISO_BCU.get(currency))
    return list

def _get_rates_from_result(result):
    dict = {}
    for item in result['datoscotizaciones']['datoscotizaciones.dato']:
        currency = str(int(item['Moneda']))
        if len(currency) == 3:
            currency = "0" + currency
        iso = codigo_BCU_ISO.get(currency)
        dict[iso] = 1.0/item['TCC']
    return dict

def get_updated_currency(currency_array, fecha):
    if not fecha:
        fecha = _get_rate_date()
    try:
        url = 'https://cotizaciones.bcu.gub.uy/wscotizaciones/servlet/awsbcucotizaciones?WSDL'
        client = Client(url)
        request = client.factory.create('wsbcucotizacionesin')
        array = client.factory.create('ArrayOfint')
        array.item = _get_currency_list(currency_array)
        request.Moneda = array
        request.FechaDesde = fecha
        request.FechaHasta = fecha
        request.Grupo = 0
        result = client.service.Execute(request)
        rates = _get_rates_from_result(result)

    except:
        _logger.error(result)
    return rates 
