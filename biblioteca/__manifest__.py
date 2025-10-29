# -*- coding: utf-8 -*-
{
    'name': "biblioteca",
    'summary': "Sistema de Gestión de Biblioteca",
    'description': """
Sistema de Gestión de Biblioteca con multas automáticas
========================================================

Características principales:
    * Gestión de libros, autores y editoriales
    * Integración con OpenLibrary API
    * Control de préstamos con estados
    * Sistema de multas por:
        - Retraso en devolución
        - Daño leve del libro
        - Daño grave del libro
        - Pérdida del libro
    * Estados de libros (disponible, prestado, no disponible, en reparación)
    * Notificaciones automáticas por email
    * Validación de cédulas ecuatorianas
    """,
    'author': "My Company",
    'website': "https://www.yourcompany.com",
    'category': 'Uncategorized',
    'version': '1.0',
    
    # Dependencias (sin cambios)
    'depends': ['base', 'mail'],
    
    # Archivos de datos (sin cambios - todos ya existen)
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/email_template.xml',
        'data/cron.xml',
        'views/views.xml',
        'views/configuracion_views.xml',
    ],
    
    # Assets (sin cambios)
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