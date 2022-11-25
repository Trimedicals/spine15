# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Base Address mx',
    'version' : '15.1',
    'summary': 'Agrega campos para Contacto mx',
    'sequence': 30,
    'description': """
    Agrega campos para Contacto mx

    """,
    'category' : 'Tools',
    'website': 'http://zeval.com.mx/',
    'author': 'silvau',
    'depends' : ['base',
        'l10n_mx_edi',
        'l10n_mx_edi_extended',
        ],
    'data': [
     'data/res_country_data.xml',
    ],
    'license': 'LGPL-3',
}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
