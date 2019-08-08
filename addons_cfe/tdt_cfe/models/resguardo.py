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

class UcfeException(Exception):
    def __init__(self, code, msg):
        if type(msg) == requests.Response:
            msg = msg._content.decode("utf-8")
        super(UcfeException, self).__init__("Problema con el CAE: Error %d; %s" % (code, msg))

_logger = logging.getLogger(__name__)

codigos_error_ucfe = {
        '01':u'CFE rechazada, no volver a emitir la factura/ticket o notas de crédito/débito asociadas a esta factura/ticket',
        '05':u'CFE rechazada, no volver a emitir la factura/ticket o notas de crédito/débito asociadas a esta factura/ticket',
        '03':u'Existe un problema con la configuración de UCFE, configure correctamente los parámetros y vuelva a emitir la factura/ticket',
        '89':u'Existe un problema con la configuración de UCFE, configure correctamente los parámetros y vuelva a emitir la factura/ticket',
        '30':u'Falta algún campo requerido para el mensaje que se está enviando. Revise los datos y emita la factura/ticket nuevamente',
        '31':u'Falta algún campo requerido para el mensaje que se está enviando. Revise los datos y emita la factura/ticket nuevamente',
        '96':u'Error interno en UCFE por más información llame al 2707 77 78 o contactese con "contacto@uruware.com"'
        }

codigos_exito_ucfe = {
        '00':'CFE aceptado definitivamentev en DGI, no volver a emitir',
        '11':'CFE aceptado, aún falta la confirmación definitivamentev en DGI, no volver a emitir'
        }

class AccountJournal(models.Model):
    _inherit = 'account.journal'
    type = fields.Selection(selection_add=[('retencion_impositiva', 'Retención Impositiva')])

    def open_resguardo_tree(self):
        """
        return {
            'name': 'Resguardos',
            'view_type': 'tree',
            'view_mode': 'tree',
            'view_id': self.env.ref('tdt_cfe.resguardo_tree').id,
            'res_model': 'tdt_cfe.account.resguardo',
            'type': 'ir.actions.act_window',
        }
        """
        [action] = self.env.ref('tdt_cfe.act_open_resguardo_tree').read()
        if not action:
            raise Warning('The action open_action_resguardo_tree could not be located in the stystem')
            return False
        ctx = self._context.copy()
        action['context'] = ctx
        action['domain'] = self._context.get('use_domain', [])
        action['display_name'] = 'Resguardos'
        return action

class ResguardoLineTotals(models.Model):
    _name = "tdt_cfe.account.resguardo.line_totals"
    cod_retencion = fields.Char(string="Código de retención")
    amount_retained = fields.Monetary(string="Amount retained", default=0, readonly="True")
    resguardo_id = fields.Many2one('tdt_cfe.account.resguardo', string="Resguardo", required="True", readonly="True")
    currency_id = fields.Many2one('res.currency', string='Moneda', required="True", related="resguardo_id.currency_id", readonly="True")

class ResguardoLine(models.Model):
    _name = "tdt_cfe.account.resguardo.line"
    tax_id = fields.Many2one('account.tax', string="Impuesto retenido") 
    tax_rate = fields.Float(string="Tasa", related="tax_id.amount", readonly="True")
    cod_retencion = fields.Char(string="Código de retención")
    amount_total = fields.Monetary(string="Amount")
    amount_retained = fields.Monetary(string="Amount retained", compute="_compute_amount_retained", readonly="True")
    resguardo_id = fields.Many2one('tdt_cfe.account.resguardo', string="Resguardo", required="True", readonly="True")
    currency_id = fields.Many2one('res.currency', string='Moneda', required="True", related="resguardo_id.currency_id", readonly="True")

    @api.depends('amount_total', 'tax_rate')
    def _compute_amount_retained(self):
        for record in self:
            record.amount_retained = record.amount_total * record.tax_rate / 100

class Resguardo(models.Model):
    _name = 'tdt_cfe.account.resguardo'
    uuid = fields.Char("Universally unique identifier")
    date_resguardo = fields.Date(string='Fecha del resguardo',
        readonly=True, states={'draft': [('readonly', False)]}, index=True,
        help="Keep empty to use the current date", copy=False, default=datetime.date.today())
    state = fields.Selection([
        ('draft','Draft'),
        ('open', 'Open'),
        ('paid', 'Paid'),
        ('cancel', 'Cancelled'),
        ], string='Status', index=True, readonly=True, default='draft', track_visibility='onchange', copy=False,)
    tax_id = fields.Many2one('account.tax', string="Impuesto retenido") 
    company_id = fields.Many2one('res.company', string='Company', change_default=True,)
    partner_id = fields.Many2one('res.partner', string='Customer', change_default=True,)
    sequence_number_next = fields.Char(string='Next Number', compute="_get_sequence_number_next", )
    sequence_number_next_prefix = fields.Char(string='Next Number', compute="_get_sequence_prefix")
    amount_total = fields.Monetary(string="Amount", compute="_get_total")
    resguardo_line_ids = fields.One2many("tdt_cfe.account.resguardo.line", "resguardo_id", string="Detalle")
    resguardo_line_totals_ids = fields.One2many("tdt_cfe.account.resguardo.line_totals", "resguardo_id", string="Totales")
    cfe_qr_img = fields.Binary('Imagen QR', copy=False)
    cfe_serie = fields.Char(string='Serie', readonly=True, copy=False)
    cfe_numero = fields.Integer(string=u'Número', readonly=True, copy=False)
    cfe_fecha_hora_firma = fields.Char(string='Fecha/Hora de firma', readonly=True)
    cfe_url_para_verificar_qr = fields.Char(string=u'Código QR', readonly=True)
    cfe_url_para_verificar_texto = fields.Char(string=u'Verificación', readonly=True)
    cfe_cae_desde_nro = fields.Integer(string='CAE Desde', readonly=True)
    cfe_cae_hasta_nro = fields.Integer(string='CAE Hasta', readonly=True)
    cfe_caena = fields.Char(string=u'CAE Autorización', readonly=True)
    cfe_caefa = fields.Char(string=u'CAE Fecha de autorización', readonly=True)
    cfe_caefd = fields.Date(string='CAE vencimiento', readonly=True)
    cfe_tipo = fields.Integer(string='Tipo de CFE', readonly=True)
    cfe_hash = fields.Char(string='Firma', readonly=True)
    move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True, index=True, ondelete='restrict', copy=False, help="Link to the automatically generated Journal Items.")

    def _get_total(self):
        for record in self:
            record.amount_total = 0
            for line in record.resguardo_line_ids:
                record.amount_total = record.amount_total + line.amount_retained

    @api.depends('currency_id')
    def tipo_de_cambio(self):
        for record in self:
            if not record.not_in_pesos():
                raise Warning('Se solicitó tipo de cambio, pero la moneda es UYU')
                return False
            curr = self.env['res.currency'].search([('name', '=', record.currency_id.name)])
            if curr and curr.rate:
                return float('%.3f'%(curr.rate))
            else:
                raise Warning('La moneda o la tasa de cambio de la moneda no están establecidas')
                return False

    def _get_pesos(self):
        pesos = self.env['res.currency'].search([('name', '=', 'UYU')])
        if not pesos:
            raise Warning("UYU currency not found in the system")
            return False
        return pesos

    def _default_journal(self):
        journal = self.env['account.journal'].search([('name', '=', 'Resguardos')])   
        if not journal:
            raise Warning("'Resguardos' journal not found")
            return False
        return journal


    journal_id = fields.Many2one('account.journal', string='Journal',
            required=True, readonly=True, states={'draft': [('readonly', False)]},
            default=_default_journal
            )
    currency_id = fields.Many2one('res.currency', string='Moneda', default=_get_pesos)

    @api.depends('state', 'journal_id', 'date_resguardo')
    def _get_sequence_prefix(self):
        for resguardo in self:
            journal_sequence = resguardo.journal_id.sequence_id
            if (resguardo.state == 'draft'): 
            #and not self.search(domain, limit=1):
                prefix, dummy = journal_sequence.with_context(ir_sequence_date=resguardo.date_resguardo, ir_sequence_date_range=resguardo.date_resguardo)._get_prefix_suffix()
                resguardo.sequence_number_next_prefix = prefix
            else:
                resguardo.sequence_number_next_prefix = False

    @api.depends('state', 'journal_id')
    def _get_sequence_number_next(self):
        for resguardo in self:
            journal_sequence = resguardo.journal_id.sequence_id
            if (resguardo.state == 'draft'):
            #and not self.search(domain, limit=1):
                number_next = journal_sequence.number_next_actual
                resguardo.sequence_number_next = '%%0%sd' % journal_sequence.padding % number_next
            else:
                resguardo.sequence_number_next = ''

    @api.depends('sequence_number_next_prefix', 'sequence_number_next')
    def _get_name(self):
        for resguardo in self:
          #  resguardo.name = resguardo.sequence_number_next_prefix + resguardo.sequence_number_next
            resguardo.name = "pepe" 

    name = fields.Char(compute="_get_name")

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
        #self.write({'cfe_qr_img': img_str})
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


    def _create_totals(self):
        for record in self:
            totals = []
            cod_ret = []
            for line in record.resguardo_line_ids:
                if line.cod_retencion not in cod_ret:
                    cod_ret.append(line.cod_retencion)
            for cod in cod_ret:
                total = 0
                lines = self.env['tdt_cfe.account.resguardo.line'].search(['&', ('cod_retencion', '=', cod), ('resguardo_id', '=', record.id)])
                for l in lines:
                    total = total + l.amount_retained
                totals.append((0, 0, {
                    'cod_retencion': cod, 
                    'amount_retained': total,
                    'resguardo_id': record.id,
                }))
            record.resguardo_line_totals_ids = totals

    def respuesta_ucfe(self):
        if not self.cfe:
            raise Warning(u'No se ha emitido el cfe, por lo tanto no hay código de respuesta de ucfe')
        tree = xmltodict.parse(self.cfe)
        for element in tree:
            print(element)
        print(tree)
        return tree['RespBody']['Resp']['a:CodRta']

    def validar_cliente(self):
        if not self.partner_id.vat:
            raise Warning('El VAT del cliente no está definido')
        if not self.partner_id.street:
            raise Warning('La calle del cliente no está definida')
        if not self.partner_id.city:
            raise Warning('La ciudad del cliente no está definida')
        if not self.partner_id.name:
            raise Warning('El nombre del cliente no está definido')
        if not self.partner_id.state_id.name:
            raise Warning('El nombre del departamento del cliente no está definido')



    def validar_empresa(self):
        if not self.company_id.vat:
            raise Warning('El VAT de la empresa no está definido')
        if not self.company_id.street:
            raise Warning('La calle de la empresa no está definida')
        if not self.company_id.city:
            raise Warning('La ciudad de la empresa no está definida')
        if not self.company_id.name:
            raise Warning('El nombre de la empresa no está definido')
        if not self.company_id.state_id.name:
            raise Warning('El nombre del departamento de la empresa no está definido')
        if not self.company_id.codigo_dgi_sucursal:
            raise Warning('El código de sucursal de DGI no está definido')

    def validar_datos(self):
        self.validar_cliente()
        self.validar_empresa()
        if not self.date_resguardo:
            raise UserError(_("Porfavor ingrese fecha del resguardo"))

    def _validar_resguardo(self):
        self.validar_datos()
        self._create_totals()
        docargs = {
                'doc_ids': [self.id],
                'doc_model': 'tdt_cfe.account.resguardo',
                'docs': self,
                }
        nombre_vista = 'tdt_cfe.cfe_resguardo'
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
                'TipoCfe': '182',
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
                for line in self.resguardo_line_totals_ids:
                    line.unlink()
                raise UcfeException(res.status_code, codigos_error_ucfe[respuesta_ucfe])

    @api.depends('currency_id', 'partner_id', 'journal_id', 'amount_retained')
    def create_account_move(self):
        account_deudores = self.env['account.account'].search([('code', '=', '113000')])
        account_retencion_iva = self.env['account.account'].search([('code', '=', '115060')])
        for record in self:
            lines = []
            lines.append((0, 0, {
                'credit': record.amount_total,
                'currency_id': record.currency_id.id,
                'partner_id': record.partner_id.id,
                'account_id': account_deudores.id,

            }))
            lines.append((0, 0, {
                'debit': record.amount_total,
                'currency_id': record.currency_id.id,
                'partner_id': record.partner_id.id,
                'account_id': account_retencion_iva.id,

            }))
            record.move_id = [(0, 0, {
                'date': datetime.datetime.now(),
                'journal_id': record.journal_id.id,
                'currency_id': record.currency_id.id,
                'partner_id': record.partner_id.id,
                'line_ids': lines,
            })]

        return False

    def action_resguardo_open(self):
        to_open_resguardos = self.filtered(lambda inv: inv.state != 'open')
        if to_open_resguardos.filtered(lambda inv: inv.state != 'draft'):
            raise UserError(_("Resguardo must be in draft state in order to validate it."))
        if self._validar_resguardo():         
            self.state = 'open'
            self.create_account_move()

