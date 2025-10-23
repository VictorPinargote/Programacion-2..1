# -*- coding: utf-8 -*-
{
    'name': "biblioteca",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Sistema de Gestión de Biblioteca
==================================

Características principales:
* Gestión de libros, autores y editoriales
* Sistema de préstamos con fechas automáticas
* Búsqueda integrada con OpenLibrary API
* **Generación automática de multas por retraso**
* **Envío automático de correos electrónicos a lectores**
* Configuración personalizable de días de préstamo y multas
* Validación de cédula ecuatoriana
* Historial completo de préstamos y multas

Sistema de Notificaciones Automáticas:
* Cron job que verifica préstamos vencidos diariamente
* Envío automático de correos cuando se genera una multa
* Días de gracia configurables antes de enviar notificación
* Plantillas de correo profesionales y personalizadas
* Cálculo automático de multas por día de retraso
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'mail',  # Necesario para el sistema de correos
    ],
    
    # Archivos de datos que se cargan siempre
    'data': [
        # Seguridad
        'security/ir.model.access.csv',
        # Secuencias
        'data/sequence.xml',
        # Plantilla de correo (debe cargarse antes de las vistas)
        'data/email_template.xml',
        # Cron job para verificación automática
        'data/cron.xml',
        # Vistas principales
        'views/views.xml',
        # Vista de configuración
        'views/configuracion_views.xml',
        #'views/template.xml'
        #'views/templates.xml',
    ],
    
    # only loaded in demonstration mode
    #'demo': [
     #   'demo/demo.xml',
    #],
    
    # Assets para JavaScript
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

#12.5.0 Nos indica que cambio ha tenido el software, el tercero, son cosas pequeñas tipo errores ortograficos, errores que habia, el segundo es el cambio de la lógica, y el primero es un cambio mucho mas robuzto que cambia toda la estructura.*/
#Depende de donde este el cambio, se hacen los test, si el tercero lo actualizo nomas, el segundo depende pero no hay que ser muchas pruebas el primero si o si toca hacer pruebas robustas*/