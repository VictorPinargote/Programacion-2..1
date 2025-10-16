{
    'name': "Biblioteca (Estructura Definida)",
    'summary': "Gestión completa y concisa de Préstamos, Multas, Usuarios y Libros.",
    'description': """
        Módulo funcional para una biblioteca, respetando la estructura de carpetas definida.
        Incluye gestión de usuarios, libros, préstamos, y multas por vencimiento.
    """,
    'author': "Tu Nombre",
    'category': 'Biblioteca',
    'version': '17.0.1.0.0',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'AGPL-3',
}