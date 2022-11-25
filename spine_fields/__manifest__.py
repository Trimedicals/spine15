# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Spine Fields',
    'version' : '15.1',
    'summary': 'Agrega campos para Rentas y Facturas',
    'sequence': 30,
    'description': """
    Agrega campos para Rentas y Facturas

    """,
    'category' : 'Tools',
    'website': 'http://zeval.com.mx/',
    'author': 'silvau',
    'depends' : ['base',
        'sale_renting',
        'account',
        ],
    'data': [
        'views/account_move_view.xml',
        'views/sale_order_view.xml',
    ],
    'license': 'LGPL-3',
}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
