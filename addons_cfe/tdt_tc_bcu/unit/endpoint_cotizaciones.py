# -*- coding: utf-8 -*-
import requests
import datetime
import urllib
import json

host = 'http://www.bcu.gub.uy'
handler = '/_layouts/BCU.Cotizaciones/handler/CotizacionesHandler.ashx?op=getcotizaciones'
endpoint = 'http://www.bcu.gub.uy' + handler

# solo es necesario mandar el Val, que es el codigo iso de la moneda.
# la cotizacion va contra el peso uruguayo

cotizaciones = {
    'USD':{"Val":"2225","Text":"DLS. USA BILLETE"},
    'UI':{"Val":"9800","Text":"UNIDAD INDEXADA"},
    'UR':{"Val":"9900","Text":"UNIDAD REAJUSTAB"},
    'ARS':{"Val":"0501","Text":"PESO ARG.BILLETE"},
    'BRL':{"Val":"1001","Text":"REAL BILLETE"},
}
def get_cotizacion_usd_dia():
    return json.loads(get_cotizaciones(monedas = [cotizaciones['USD']]).content)['cotizacionesoutlist']['Cotizaciones'][0]['TCC']

# llama a la interface del BCU que se usa en la página para obtener cotizaciones desde su web
# 
#esta función por ahora solo trae para dolar, ui y euro, aunque se puede hacer más genérica
#se necesitarían configurar los iso codes de cada moneda que se quiera traer
def get_cotizaciones(fechaInicio = (datetime.datetime.today() - datetime.timedelta(days=1)).strftime("%d/%m/%Y"),
                     fechaFin = (datetime.datetime.today() - datetime.timedelta(days=1)).strftime("%d/%m/%Y"),
                     monedas = [v for k,v in cotizaciones.items()]):
    body = { "KeyValuePairs": {
                    "Monedas":monedas,
                    "FechaDesde":fechaInicio,
                    "FechaHasta":fechaFin,
                    "Grupo":"2"
                }

            }
    return requests.post(endpoint,data=str(body), headers = {'content-type':'application/json', 'charset':'UTF-8', 'Referer': 'http://www.bcu.gub.uy/estadisticas-e-indicadores/paginas/cotizaciones.aspx'})
