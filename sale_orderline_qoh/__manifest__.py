# -*- coding: utf-8 -*-

{
    'name': 'Sale Order Line Quantity on hand',
    'version': '1.0',
    'category': 'Sale',
    'sequence': 6,
    'author': 'ErpMstar Solutions',
    'summary': 'Allows to show quantity on hand in sale order line.',
    'description': "Allows to show quantity on hand in sale order line.",
    'depends': ['sale','stock'],
    'data': [
        'views/views.xml',
        
    ],
    'qweb': [
        # 'static/src/xml/web.xml',
    ],
    'images': [
        'static/description/a1.jpg',
    ],
    'installable': True,
    'website': '',
    'auto_install': False,
    'price': 9,
    'currency': 'EUR',
}
