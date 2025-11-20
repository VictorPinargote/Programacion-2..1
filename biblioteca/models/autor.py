from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta

class BibliotecaAutor(models.Model):
    _name = 'biblioteca.autor'
    _description = 'biblioteca.autor'
    _rec_name = 'nombre_autor'

    nombre_autor = fields.Char(string='Nombre del Autor')
    apellido_autor = fields.Char(string='Apellido del Autor')
    nacimiento_autor = fields.Date()
    pseudonimo_autor = fields.Char(string='Pseudonimo del Autor')

    libros = fields.Many2one(
        'biblioteca.libro',
        string='Libros Publicados',
        colum1='autor_id',
        colum2='libro_id'
    )

    @api.depends('nombre_autor', "apellido_autor")
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.nombre_autor}  {record.apellido_autor}"
