# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class Partner(models.Model):
    _inherit = 'res.partner'



    @api.model
    def _address_fields(self):
        res = super(Partner,self)._address_fields()
        res.append('l10n_mx_edi_colony')
        res.append('l10n_mx_edi_locality')
        res.append('city_id')
        """Returns the list of address fields that are synced from the parent."""
        return res


    

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
