from openerp import models,fields;

class config_ucfe(models.Model):
    _name = "config.ucfe"

    name = fields.Char("Name",translate=True)
    value = fields.Char("Value",translate=True)
    order = fields.Integer("Order")
    product_id = fields.Many2one('product.template','Associated product')


