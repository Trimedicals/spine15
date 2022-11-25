# -*- coding: utf-8 -*-
{
    'name': "Validar Facturas",

    'summary': """
        Revisa que las facturas de proveedor sean válidas en el SAT
    """,

    'description': """
        Agrega un wizard para verificar la autenticidad del comprobante fiscal del SAT que se quiere asociar a la factura del proveedor.
        Se deben definir el pac_host, pac_user y pac_password del proveedor de validacion. El usuario y password se toman del company si no se especifican
    """,

    'author': "silvau",
    'website': "http://www.zeval.com.mx",

    'category': 'Accounting & Finance',
    'version': '15.1',

    'depends': [
        'purchase',
        'l10n_mx_edi'
    ],

    'data': [
        'data/cron.xml',
        'security/ir.model.access.csv',
        'views/invoice_view.xml',
        'views/res_config_settings_view.xml',
        'wizard/subir_factura_view.xml',
    ],

    'license': 'AGPL-3',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
