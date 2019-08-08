# -*- coding: utf-8 -*-
from odoo import models, fields, api
import requests
import datetime
import uuid as guid_generator
import json
import xmltodict
import logging
import re
import qrcode
import base64
from io import StringIO, BytesIO
import tempfile
from ...tdt_tc_bcu import unit
from odoo.exceptions import ValidationError, UserError, Warning


class UcfeException(Exception):
    def __init__(self, code, msg):
        if type(msg) == requests.Response:
            msg = msg._content.decode("utf-8")
        super(UcfeException, self).__init__(
            "Problema con el CAE: Error %d; %s" % (code, msg))


_logger = logging.getLogger(__name__)

codigos_error_ucfe = {
        '01': u'CFE rechazada, no volver a emitir la factura/ticket o notas de crédito/débito asociadas a esta factura/ticket',
        '05': u'CFE rechazada, no volver a emitir la factura/ticket o notas de crédito/débito asociadas a esta factura/ticket',
        '03': u'Existe un problema con la configuración de UCFE, configure correctamente los parámetros y vuelva a emitir la factura/ticket',
        '89': u'Existe un problema con la configuración de UCFE, configure correctamente los parámetros y vuelva a emitir la factura/ticket',
        '30': u'Falta algún campo requerido para el mensaje que se está enviando. Revise los datos y emita la factura/ticket nuevamente',
        '31': u'Falta algún campo requerido para el mensaje que se está enviando. Revise los datos y emita la factura/ticket nuevamente',
        '96': u'Error interno en UCFE por más información llame al 2707 77 78 o contactese con "contacto@uruware.com"'
        }

codigos_exito_ucfe = {
        '00': 'CFE aceptado definitivamentev en DGI, no volver a emitir',
        '11': 'CFE aceptado, aún falta la confirmación definitivamentev en DGI, no volver a emitir'
        }

codigos_cfe = {
        'ticket': 101,
        'nc-ticket': 102,
        'nd-ticket': 103,
        'factura': 111,
        'nc-factura': 112,
        'nd-factura': 113,
        'factura-exp': 121,
        'nc-factura-exp': 122,
        'nd-factura-exp': 123,
        'remito-exp': 124,
        'remito': 181
        }

class double_quote_dict(dict):
    def __str__(self):
        return json.dumps(self)

class invoice(models.Model):
    _inherit = 'account.invoice'
    cfe = fields.Text("CFE")  # Guardar por 10 años
    # Si el invoice no tiene uuid al momento de enviar cfe se genera uno automaticamente
    uuid = fields.Char("Universally unique identifier")
    ui = fields.Float(string="Tasa Unidad Indexada") #field sin uso
    tipo_cfe = fields.Integer("Tipo CFE")
    cfe_emitido = fields.Boolean("CFE Emitido", copy=False, default=False)
    company_ruc = fields.Char("Company RUC", related="company_id.vat")
    # Campos que se necesitan en la factura
    cfe_fecha_hora_firma = fields.Char(
        string='Fecha/Hora de firma', readonly=True)
    cfe_url_para_verificar_qr = fields.Char(string=u'Código QR', readonly=True)
    cfe_url_para_verificar_texto = fields.Char(
        string=u'Verificación', readonly=True)
    cfe_cae_desde_nro = fields.Integer(string='CAE Desde', readonly=True)
    cfe_cae_hasta_nro = fields.Integer(string='CAE Hasta', readonly=True)
    cfe_caena = fields.Char(string=u'CAE Autorización', readonly=True)
    cfe_caefa = fields.Char(string=u'CAE Fecha de autorización', readonly=True)
    cfe_caefd = fields.Date(string='CAE vencimiento', readonly=True)
    cfe_tipo = fields.Integer(string='Tipo de CFE', readonly=True)
    cfe_hash = fields.Char(string='Firma', readonly=True)
    cfe_contingencia = fields.Boolean('Es Contingencia', default=False)
    cfe_serie_contingencia = fields.Char(string='Serie', size=3)
    cfe_nro_contingencia = fields.Integer(string=u'Número')
    cfe_qr_img = fields.Binary('Imagen QR', copy=False)
    cfe_serie = fields.Char(string='Serie', readonly=True, copy=False)
    cfe_numero = fields.Integer(string=u'Número', readonly=True, copy=False)
    nc_motivo = fields.Char(string= 'Motivo', size=90)

    @api.model
    def create(self, vals):
        vals['uuid'] = str(guid_generator.uuid4())
        return super(invoice, self).create(vals)

    @api.model
    def tasa_minima(self):
        return self.env.ref('tdt_cfe.tasa_minima_incluida_en_precio').amount

    @api.model
    def tasa_basica(self):
        return self.env.ref('tdt_cfe.tasa_basica_incluida_en_precio').amount

    @api.depends('currency_id')
    def not_in_pesos(self):
        for record in self:
            return record.currency_id.name != 'UYU'

    @api.depends('ui', 'amount_total')
    def monto_mayor_diez_mil_ui(self):
        for record in self:
            ui = record.unidad_indexada()
            if record.amount_total and ui:
                if record.amount_total > (10000 / ui):
                    return True
                else:
                    return False
            else:
                if not record.amount_total:
                    raise Warning('El monto total no está establecido')
                if not ui:
                    raise Warning('La tasa de la unidad indexada no está establecida')


    @api.depends('currency_id')
    def unidad_indexada(self):
        ui_curr = self.env.ref("tdt_tc_bcu.BCU_UI")
        #TODO: return latest rate directly
        ui_rates = self.env['res.currency.rate'].search(['&', ('company_id', '=', self.company_id.id), ('currency_id', '=', ui_curr.id)])
        if ui_rates[0]:
            ui_rate = ui_rates[0]
        for rate in ui_rates:
            if rate.write_date > ui_rate.write_date:
                ui_rate = rate
        if ui_rate.rate:
            return ui_rate.rate
        else:
            raise Warning('Hubo un problema al cargar el último valor registrado de la unidad indexada')

    @api.depends('currency_id')
    def tipo_de_cambio(self):
        for record in self:
            if not record.not_in_pesos():
                raise Warning('Se solicitó tipo de cambio, pero la moneda es UYU')
            curr = self.env['res.currency'].search([('name', '=', record.currency_id.name)])
            if curr and curr.rate:
                return float('%.3f'%(curr.rate))
            else:
                raise Warning('La moneda o la tasa de cambio de la moneda no están establecidas')

    def respuesta_ucfe(self):
        if not self.cfe:
            raise Warning(u'No se ha emitido el cfe, por lo tanto no hay código de respuesta de ucfe')
        tree = xmltodict.parse(self.cfe)
        for element in tree:
            print(element)
        print(tree)
        return tree['RespBody']['Resp']['a:CodRta']

    def get_ui(self):
        cotizaciones = unit.endpoint_cotizaciones.get_cotizaciones()
        return cotizaciones

    def tiene_receptor(self):
        if not self.partner_id:
            raise Warning('Error, partner vacio')
        return self.partner_id.id != self.env.ref('tdt_cfe.partner_sin_receptor').id

    def requiere_receptor(self):
        if self.partner_es_empresa_uy():
            return True
        UI = self.env.ref("tdt_l10n_definiciones.BCU_UI").rate
        if self.amount_untaxed >= 10000 * UI:
            return True
        return False

    @api.depends('cfe_emitido', 'cfe_numero')
    def numero_cfe(self):
        for record in self:
            if not self.cfe_emitido:
                raise Warning(u'No se ha emitido el cfe, por lo tanto no hay número de cfe')
            if record.cfe_numero:
                return record.cfe_numero
            else:
                raise Warning('El número de cfe no está establecido')

    @api.depends('cfe_emitido', 'cfe_serie')
    def serie(self):
        for record in self:
            if not self.cfe_emitido:
                raise Warning(u'No se ha emitido el cfe, por lo tanto no hay serie')
            if record.cfe_serie:
                return record.cfe_serie
            else:
                raise Warning('El número de serie no está establecido')

    @api.depends('origin')
    def nc_tiene_origen(self):
        self.ensure_one()
        for record in self:
            if not record.es_nota_credito():
                raise Warning('El método nc_tiene_origen fue llamado para un record que no es una nota de crédito')
            if not record.origin:
                return False
            res = self.env['account.invoice'].search([('number','=', record.origin)])
            if len(res) == 0:
                return False
            else:
                return True
    
    @api.depends('origin')
    def obtener_factura_original(self):
        #precondición: self.nc_tiene_origen()
        self.ensure_one()
        for record in self:
            res = self.env['account.invoice'].search([('number','=', record.origin)])
            if len(res) == 1:
                return res
            else:
                raise Warning('El origen de esta nota de crédito referencia a varias facturas/tickets')

    @api.depends('partner_id')
    def partner_es_extranjero(self):
        return self.partner_id.country_id.code != 'UY'

    @api.depends('partner_id')
    def partner_es_empresa(self):
        return self.partner_id.company_type == 'company'

    @api.depends('tipo_documento', 'partner_id')
    def partner_es_empresa_uy(self):
        if (self.partner_id.tipo_documento == 2 and self.partner_id.vat and not self.partner_es_extranjero()):
            return True
        return False

    @api.depends('type')
    def es_nota_credito(self):
        # Refiere al invoice de odoo, no al cfe
        return self.type == 'out_refund'

    @api.depends('type')
    def es_factura(self):
        """
        Devuelve true si es factura o ticket, False si es nota credito
        Refiere al invoice de odoo, no al cfe
        """
        return self.type == 'out_invoice'

    @api.depends('tipo_cfe')
    def es_e_factura(self):
        self.ensure_one()
        for record in self:
            tipo = record.tipo_cfe
            return (tipo == codigos_cfe['factura'] or tipo == codigos_cfe['nc-factura']) 

    @api.depends('tipo_cfe')
    def es_e_ticket(self):
        self.ensure_one()
        for record in self:
            tipo = record.tipo_cfe
            return (tipo == codigos_cfe['ticket'] or tipo == codigos_cfe['nc-ticket'])

    def es_e_ticket_comun(self):
        for record in self:
            return (record.es_e_ticket() and not record.monto_mayor_diez_mil_ui())

    def es_e_ticket_rut_extranjero(self):
        return self.es_e_ticket() and self.partner_es_empresa() and self.partner_id

    @api.depends('tipo_cfe')
    def es_e_factura_exp(self):
        if self.tipo_cfe == codigos_cfe['factura-exp']:
            return True
        if self.es_nota_credito():
            if self.nc_tiene_origen():
                factura_original = self.obtener_factura_original()
                return factura_original.tipo_cfe == codigos_cfe['factura-exp']
        else:
            return False

    def url_to_qr(self):
        tree = xmltodict.parse(self.cfe)
        try:
            tree['RespBody']['Resp']['a:DatosQr']
        except:
            ValueError()
        url = tree['RespBody']['Resp']['a:DatosQr']

        qr = qrcode.QRCode(version=1,error_correction=qrcode.constants.ERROR_CORRECT_L,box_size=20,border=4,)
        qr.add_data(url) #you can put here any attribute SKU in my case
        qr.make(fit=True)
        img = qr.make_image()
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_str = base64.b64encode(buffer.getvalue())
        # self.write({'cfe_qr_img': img_str})
        self.cfe_qr_img = img_str

    def campos_llenar_campos_cfe(self):
        """
        Llena los campos de la pagina "Factura Electronica"

        :return:
        """
        tree = xmltodict.parse(self.cfe)
        try:
            tree['RespBody']['Resp']
        except:
            ValueError()
        respuesta = tree['RespBody']['Resp']
        fecha_hora_firma = respuesta['a:FechaFirma']
        self.cfe_fecha_hora_firma = fecha_hora_firma
        url_qr = respuesta['a:DatosQr']
        self.cfe_url_para_verificar_qr = url_qr
        cae_desde = respuesta['a:CaeNroDesde']
        self.cfe_cae_desde_nro = cae_desde
        cae_hasta = respuesta['a:CaeNroHasta']
        self.cfe_cae_hasta_nro = cae_hasta
        cae_autorizacion = respuesta['a:IdCae']
        self.cfe_caena = cae_autorizacion
        cae_vencimineto = respuesta['a:VencimientoCae']
        fd_year = cae_vencimineto[0:4]
        fd_month = cae_vencimineto[4:6]
        fd_day = cae_vencimineto[6:8]
        self.cfe_caefd = fd_year + '-' + fd_month + '-' + fd_day 
        self.cfe_url_para_verificar_texto = 'http://www.ucfe.com.uy/consultacfe/'
        serie = respuesta['a:Serie']
        self.cfe_serie = serie
        numero = respuesta['a:NumeroCfe']
        self.cfe_numero = numero



    @api.one
    def facturar(self):
        """
        Identifica cuál es el tipo de cfe correspondiente a la factura
        """
        if self.partner_es_empresa():
            if self.partner_es_empresa_uy():
                # si tiene rut, la razon social del cfe va a ser el nombre del partner
                if self.es_nota_credito():
                    # Nota credito a factura
                    self.tipo_cfe = codigos_cfe['nc-factura']
                elif self.es_factura():
                    # Factura
                    self.tipo_cfe = codigos_cfe['factura']
            else:
                if self.es_nota_credito():
                    # Nota credito a ticket
                    self.tipo_cfe = codigos_cfe['nc-ticket']
                elif self.es_factura():
                    # Ticket
                    self.tipo_cfe = codigos_cfe['ticket']
        else:
                if self.es_nota_credito():
                    # Nota credito a ticket
                    self.tipo_cfe = codigos_cfe['nc-ticket']
                elif self.es_factura():
                    # Ticket
                    self.tipo_cfe = codigos_cfe['ticket']
                else:
                    raise Warning('Bad set up')
        self.cfe_emitido = self._facturar()

    @api.one
    def _facturar(self):
        self.ensure_one()
        self.validar_datos()
        docargs = {
                'doc_ids': [self.id],
                'doc_model': 'account.invoice',
                'docs': self,
                }

        nombre_vista = 'tdt_cfe.cfe'
        view = self.env.ref(nombre_vista)
        cfe = view.render_template(nombre_vista, docargs)
        now = datetime.datetime.now()
        company = self.env.user.company_id
        if not self.uuid:
            self.uuid = str(guid_generator.uuid4())
        requerimiento = {
                'CfeXmlOTexto' : re.sub(r'[\n\r]|  ', '', cfe.decode('UTF-8')),
                'CodComercio' : company.codigo_comercio,
                'CodTerminal' : company.codigo_terminal,
                'EmailEnvioPdfReceptor':company.email_pdfs,
                'FechaReq' : str(now.year) + str(now.month) + str(now.day),
                'HoraReq' : str(now.hour) + str(now.minute),
                'IdReq': "0", ## Valor arbitrario
                'TipoCfe': str(self.tipo_cfe),
                'TipoMensaje': 310, ## firma y envio de CFE, por ahora solo usamos este código
                'Uuid': self.uuid
                }
        body = json.dumps({
            'RequestDate' : datetime.datetime.now().isoformat(),
            'Tout': 40000,
            'CodComercio' : company.codigo_comercio,
            'CodTerminal' : company.codigo_terminal,
            'Req': requerimiento,
            })
        token = base64.b64encode((company.usuario_ucfe + ':' + company.pass_ucfe).encode('UTF-8')).decode('UTF-8')
        _headers = {
                'Authorization':   'Basic ' + token,
                'Content-Type':    'application/json',
                }
        url = company.url_ucfe
        _logger.info(_headers)
        res = requests.post(url , headers = _headers, data = body)
        _logger.info(res.text)
        if res.status_code >= 300:
            raise UcfeException(res.status_code, res)
        self.cfe = res._content
        respuesta_ucfe = self.respuesta_ucfe()
        if respuesta_ucfe:
            if respuesta_ucfe in codigos_exito_ucfe:
                self.url_to_qr()
                self.campos_llenar_campos_cfe()
                return True
            if respuesta_ucfe in codigos_error_ucfe:
                raise UcfeException(res.status_code, codigos_error_ucfe[respuesta_ucfe])

        raise UcfeException(res.status_code, res)

    def validar_cliente(self):
        for record in self:
            if not record.es_e_ticket_comun():
                if not record.partner_id.vat:
                    raise Warning('El VAT del cliente no está definido')
                if not record.partner_id.street:
                    raise Warning('La calle del cliente no está definida')
                if not record.partner_id.city:
                    raise Warning('La ciudad del cliente no está definida')
                if not record.partner_id.name:
                    raise Warning('El nombre del cliente no está definido')
                if not record.partner_id.state_id.name:
                    raise Warning('El nombre del departamento del cliente no está definido')

    def validar_empresa(self):
        for record in self:
            if not record.company_id.vat:
                raise Warning('El VAT de la empresa no está definido')
            if not record.company_id.street:
                raise Warning('La calle de la empresa no está definida')
            if not record.company_id.city:
                raise Warning('La ciudad de la empresa no está definida')
            if not record.company_id.name:
                raise Warning('El nombre de la empresa no está definido')
            if not record.company_id.state_id.name:
                raise Warning('El nombre del departamento de la empresa no está definido')
            if not record.company_id.codigo_dgi_sucursal:
                raise Warning('El código de sucursal de DGI no está definido')


    def validar_datos(self):
        self.validar_cliente()
        self.validar_empresa()
        errores = []
        errores_receptor = []
        if not self.date_invoice:
            errores.append(u'Ingrese fecha de facturación' )
        if not self.invoice_line_ids:
            errores.append(u'Debe haber al menos un producto/servicio a facturar')
        """
        if self.tiene_receptor():
            if not self.partner_id.tipo_documento:
                errores_receptor.append(u'tipo de documento')
            if not self.partner_id.vat:
                errores_receptor.append(u'número de documento')
            if self.partner_es_empresa:
                if not self.partner_id.street:
                    errores_receptor.append(u'dirección')
                if not self.partner_id.city:
                    errores_receptor.append(u'ciudad')
        msje_error = u''
        for e in errores:
            msje_error += u'\n'+e
        if errores_receptor:
            msje_error += u'\n Si ingresa receptor este debe tener '
            i = 1
            for e in errores_receptor:
                msje_error += e + (u' y ' if  len(errores_receptor) -1 == i   else u', ' if len(errores_receptor) > i else u' asignados')
                i += 1
        if msje_error:
            raise UserError(msje_error) """

    @api.one
    def action_invoice_open(self):
        if self.type not in ('in_invoice', 'in_refund'):
            sys_cfg = self.env['ir.config_parameter']
            if sys_cfg.get_param('fe_inactiva'):
                return super(invoice, self).action_invoice_open()
            if not self.date_invoice:
                self.date_invoice = fields.Date.context_today(self)
            self.facturar()
        return super(invoice, self).action_invoice_open()

    @api.one
    def factura_contingencia(self):
        return super(invoice, self).action_invoice_open()


    def monto_neto_a_tasa_minima(self):
        monto = 0
        for linea in self.invoice_line_ids:
            monto += linea.price_subtotal if linea.es_tasa_minima() else 0
        return round(monto, 2)

    def monto_neto_a_tasa_basica(self):
        monto = 0
        for linea in self.invoice_line_ids:
            monto += linea.price_subtotal if linea.es_tasa_basica() else 0
        return round(monto, 2)

    def monto_neto_sin_iva(self):
        monto = 0
        for linea in self.invoice_line_ids:
            monto += linea.price_subtotal if (not linea.es_tasa_basica() and not linea.es_tasa_minima()) else 0
        return round(monto, 2)


    def existe_monto_neto_a_tasa_minima(self):
        for linea in self.invoice_line_ids:
            if linea.es_tasa_minima():
                return True
        return False

    def existe_monto_neto_a_tasa_basica(self):
        for linea in self.invoice_line_ids:
            if linea.es_tasa_basica():
                return True
        return False

    def existe_monto_neto_sin_iva(self):
        for linea in self.invoice_line_ids:
            if not linea.es_tasa_basica() and not linea.es_tasa_minima():
                return True
        return False

    def monto_iva_a_tasa_minima(self):
        tasa_minima = self.env['account.invoice'].tasa_minima() / 100
        monto = 0
        for linea in self.invoice_line_ids:
            if not linea.iva_incluido():
                monto += (linea.price_unit * tasa_minima) * linea.quantity if linea.es_tasa_minima() else 0
            else:
                monto += (linea.price_unit * linea.quantity) - linea.price_subtotal if linea.es_tasa_minima() else 0
        return round(monto, 2)

    def monto_iva_a_tasa_basica(self):
        tasa_basica = self.env['account.invoice'].tasa_basica() / 100
        monto = 0
        for linea in self.invoice_line_ids:
            if not linea.iva_incluido():
                monto += (linea.price_unit * tasa_basica)* linea.quantity  if linea.es_tasa_basica() else 0
            else:
                monto += (linea.price_unit * linea.quantity)- linea.price_subtotal if linea.es_tasa_basica() else 0

        return round(monto, 2)

    def get_payment_type(self):
        if self.es_nota_credito() and self.nc_tiene_origen():
           ptype = self.obtener_factura_original().payment_term_id.payment_type
        else:
            ptype = self.payment_term_id.payment_type
        if ptype:
            return ptype
        else:
            raise Warning('Payment type not set')

class invoice_line(models.Model):
    _inherit = 'account.invoice.line'

    def iva_incluido(self):
        return self.invoice_line_tax_ids.price_include

    def precio_unitario(self):
        if self.iva_incluido():
            tasa_monto_neto = 1/ (1 + self.env['account.invoice'].tasa_basica() / 100) if self.es_tasa_basica() else (1/ (1 + self.env['account.invoice'].tasa_minima() / 100) if self.es_tasa_minima() else 1)
            return round(self.price_unit * tasa_monto_neto, 2)
        else:
            return round(self.price_unit, 2)


    def tasa_iva(self):
        return self.invoice_line_tax_ids.amount

    def es_tasa_basica(self):
        # return self.invoice_line_tax_ids.id == self.env.ref('l10n_uy.1_vat1').id or self.invoice_line_tax_ids.id == self.env.ref('tdt_cfe.tasa_basica_incluida_en_precio').id
        return self.invoice_line_tax_ids.amount == self.env['account.invoice'].tasa_basica()

    def es_tasa_minima(self):
        return self.invoice_line_tax_ids.amount == self.env['account.invoice'].tasa_minima()
    # return self.invoice_line_tax_ids.id == self.env.ref('l10n_uy.1_vat2').id or self.invoice_line_tax_ids.id == self.env.ref('tdt_cfe.tasa_minima_incluida_en_precio').id

    def indice_facturacion(self):
        if self.es_tasa_basica():
            return 3
        if self.es_tasa_minima():
            return 2
        if self.invoice_line_tax_ids.amount == 0:
            return 1

class CreditNoteWizard(models.TransientModel):
    _name = 'tdt_cfe.account.nc_wizard'
    invoice_id = fields.Many2one('account.invoice')

    @api.depends('invoice_id')
    def action_invoice_open(self):
        for record in self:
            record.invoice_id.action_invoice_open()
