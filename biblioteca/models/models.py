# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import timedelta

class bibliotecaWizard(models.Model):
    _name = 'biblioteca.wizard'
    _description = 'modelo biblioteca.wizard'
    
    prestamo = fields.Char(string="Nombre del Libro")
    evaluacion libro = fields.Char(string="Evaluación del Libro")
    
    
    def cerrar_prestamo(self):
        return {'type': 'ir.actions.act_window_close'}

class bibliotecalibro(models.Model):
    _name = 'biblioteca.libro'
    _description = 'modelo biblioteca.libro'
    
    codigo_libro = fields.Char(string="Código del Libro")
    name = fields.Char(string="Nombre del Libro") 
    autor = fields.Many2one('biblioteca.autor', string="Autor") #relación muchos a uno con autor
    titulo = fields.Char(string="Título", required=True)
    fecha_publicacion = fields.Date(string="Fecha de Publicación")
    ejemplares = fields.Integer(string="Número de Ejemplares")
    costo = fields.Float(string="Costo")
    categoria = fields.Char(string="categoría")
    isbn = fields.Char(string="ISBN")
    description = fields.Text(string="Descripción")
    ubicacion = fields.Char(string="Ubicación en la Biblioteca")

class bibliotecaautor(models.Model):
    
    _name = 'biblioteca.autor'
    _description = 'modelo de bibliotecaautor'
    _recname_ = 'first_name'
    
    first_name = fields.Char(string="Primer Nombre")
    last_name = fields.Char(string="Apellido")
    fecha_nacimiento = fields.Date(string="Fecha de Nacimiento")
    libros_ids = fields.Many2many('biblioteca.libro', 'autor_id', string="Libros del Autor") #relación muchos a muchos con libros

class bibliotecaprestamo(models.Model):
    _name = 'biblioteca.prestamo'
    _description = 'biblioteca.prestamo'
    
    name = fields.Char(string="Código de Préstamo")
    fecha_prestamo = fields.Date(string="Fecha de Préstamo")
    libro_id = fields.Many2one('biblioteca.biblioteca', string="Libro")
    usuario_id = fields.Many2one('biblioteca.usuario', string="Usuario")
    fecha_devolucion = fields.Date(string="Fecha de Devolución")
    multa_bol = fields.Boolean(string="¿Tiene Multa?")
    multa = fields.Float(string="Monto de la Multa")
    fecha_maxima = fields.Date(compute='_compute_devolucion_fecha_maxima', string="Fecha Máxima de Devolución", store=True)
    usuario = fields.Many2one('res.users', string="Usuario que realiza el préstamo",
                              default=lambda self: self.env.user.id) #relación muchos a uno con res.users
    estado = fields.Selection([('b', 'borrador'),
                                ('p', 'prestado'),
                                ('m', 'multa'),
                                ('d', 'devuelto')],
                               string="Estado del Préstamo", default='b')
    multas_ids = fields.One2many('biblioteca.multa', 'presta mo', string="Multas") #relación uno a muchos con multas
    
    @api .depends('fecha_maxima')
    def _compute_devolucion_fecha_maxima(self):
        for record in self:
            if record.fecha_prestamo:
                record.fecha_maxima = record.fecha_prestamo + timedelta(days=2)
            else:
                record.fecha_maxima = False
    
class bibliotecamulta(models.Model):
    
    _name = 'biblioteca.multa'
    _description = 'biblioteca.multa'
    
    name = fields.Char(string="codigo de la multa")
    multa = fields.Char(string="Descripción de la Multa")
    prestamo = fields.Many2one('biblioteca.prestamo', string="Préstamo") #relación muchos a uno con préstamo
    costo_multa = fields.Float(string="Costo de la Multa")
    fecha_multa = fields.Date(string="Fecha de multa")
    motivo = fields.selection(('pe', 'perdida'),
                              ('re', 'retrasado'),
                              ('da', 'daño'))
    
class biliotecaUsuario(models.Model):
    _name = 'biblioteca.usuario'
    _description = 'modelo de biblioteca.usuario'
    
    name = fields.Char(string="Nombre del Usuario")
    contacto = fields.Char(string="Información de Contacto")
    direccion = fields.Text(string="Dirección")
    email = fields.Char(string="Correo Electrónico")
    prestamos_ids = fields.One2many('biblioteca.prestamo', 'cliente_nombre', string="Préstamos del Usuario") #relación uno a muchos con préstamos
    multas_ids = fields.One2many('biblioteca.multa', 'usuario_nombre', string="Multas del Usuario") #relación uno a muchos con multas