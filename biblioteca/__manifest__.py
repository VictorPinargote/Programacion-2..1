# -*- coding: utf-8 -*-
{
    'name': "biblioteca",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base'],
    
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        #'views/template.xml'
        'data/sequence.xml'
        #'views/templates.xml',
    ],
    # only loaded in demonstration mode
    #'demo': [
     #   'demo/demo.xml',
    #],
    'assets': {
    'web.assets_backend': [
        'biblioteca/static/src/widgets/openlibrary_search_widget.js',
    ],
    },
    'application': True,
    'license': 'AGPL-3'
}

#12.5.0 Nos indica que cambio ha tenido el software, el tercero, son cosas pequeñas tipo errores ortograficos, errores que habia, el segundo es el cambio de la lógica, y el primero es un cambio mucho mas robuzto que cambia toda la estructura.*/
#Depende de donde este el cambio, se hacen los test, si el tercero lo actualizo nomas, el segundo depende pero no hay que ser muchas pruebas el primero si o si toca hacer pruebas robustas*/

