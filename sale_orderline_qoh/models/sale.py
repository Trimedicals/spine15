# -*- coding: utf-8 -*-


from odoo import fields, models,tools,api,_
from odoo.addons import decimal_precision as dp

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    qty_available = fields.Float('Qty On Hand', digits=dp.get_precision('Product Unit of Measure'),related='product_id.qty_available')
    virtual_available = fields.Float('Forecast', digits=dp.get_precision('Product Unit of Measure'),related='product_id.virtual_available')



