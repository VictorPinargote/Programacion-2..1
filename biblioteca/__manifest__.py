# -*- coding: utf-8 -*-
{
    'name': "biblioteca",
    'summary': "Sistema de Gestión de Biblioteca",
    'description': """
Sistema de Gestión de Biblioteca con multas automáticas
    """,
    'author': "My Company",
    'website': "https://www.yourcompany.com",
    'category': 'Uncategorized',
    'version': '1.0',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/email_template.xml',
        'data/cron.xml',
        'views/views.xml',
        'views/configuracion_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'biblioteca/static/src/widgets/openlibrary_search_widget.js',
        ],
    },
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
}