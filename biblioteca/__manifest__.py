# -*- coding: utf-8 -*-
{
    'name': "biblioteca",
    'summary': "Sistema de Gestión de Biblioteca con Multas Automáticas",
    'description': """
Sistema de Gestión de Biblioteca con Multas Automáticas
========================================================

Características principales:
    * Gestión de libros, autores y editoriales
    * Integración con OpenLibrary API para importar libros
    * Control de préstamos con múltiples copias por libro
    * Sistema inteligente de copias disponibles
    * Sistema automático de multas por:
        - Retraso en devolución (automático mediante cron job)
        - Daño leve del libro (manual al devolver)
        - Daño grave del libro (manual al devolver)
        - Pérdida del libro (manual al devolver)
    * Estados de libros: disponible, prestado, no disponible
    * Notificaciones automáticas por email cuando se genera multa
    * Validación de cédulas ecuatorianas
    * Cron job que verifica préstamos vencidos cada hora
    * Generación automática de multas en la base de datos
    * Actualización automática de multas si el retraso aumenta
    
Sistema de Multas Automáticas:
    - El cron job se ejecuta cada hora (configurable)
    - Verifica préstamos con fecha_maxima vencida
    - Genera multas automáticamente después de días de gracia
    - Envía correos de notificación automáticamente
    - Actualiza el estado del préstamo a "Con Multa"
    - Las multas se registran en la sección de Multas
    """,
    'author': "My Company",
    'website': "https://www.yourcompany.com",
    'category': 'Library Management',
    'version': '1.0',
    
    # Dependencias necesarias
    'depends': ['base', 'mail'],
    
    # Archivos de datos en orden de carga
    'data': [
        # 1. Seguridad (debe cargarse primero)
        'security/ir.model.access.csv',
        
        # 2. Secuencias (necesarias para crear registros)
        'data/sequence.xml',
        
        # 3. Plantillas de email
        'data/email_template.xml',
        
        # 4. Cron jobs (acciones programadas)
        'data/cron.xml',
        
        # 5. Vistas principales
        'views/views.xml',
        
        # 6. Vistas de configuración
        'views/configuracion_views.xml',
    ],
    
    # Assets para frontend (si los tienes)
    'assets': {
        'web.assets_backend': [
            # Descomentar si tienes widgets personalizados
            # 'biblioteca/static/src/widgets/openlibrary_search_widget.js',
        ],
    },
    
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}