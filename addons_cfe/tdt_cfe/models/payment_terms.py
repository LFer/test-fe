# -*- coding: utf-8 -*-
from odoo import models, fields

class payment_term(models.Model):
    _inherit = "account.payment.term"
    payment_type = fields.Selection(
        [("1", "Contado"),("2", u"Crédito")],
        string = "Tipo de pago",
        required="True",
    )
        
