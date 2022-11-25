# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Reportes Spine',
    'sequence': 100,
    'description': """
Reportes Spine
============================================
   1) Formato de Orden de Venta Spine
   1) Formato de Orden de Entrega Spine

    """,
    'category' : 'Reports',
    'website': 'http://zeval.com.mx/',
    'author': 'silvau',
    'depends' : [
        'spine_fields',
    ],
    'data': [
        'views/report_deliveryslip.xml',
        'views/l10n_mx_edi_report_invoice.xml',
    ],
    'license': 'LGPL-3',
}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
