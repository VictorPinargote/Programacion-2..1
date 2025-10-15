from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re
from datetime import timedelta

# -------------------------
# AUTOR y GÉNERO
# -------------------------
class Autor(models.Model):
    _name = 'biblioteca.autor'
    _description = 'Autor'
    _order = "nombre"
    nombre = fields.Char(string='Nombre Completo', required=True)
    # Relación a Libros (One2many)
    libro_ids = fields.One2many('biblioteca.libro', 'autor_id', string='Libros Publicados')

class Genero(models.Model):
    _name = 'biblioteca.genero'
    _description = 'Género'
    _order = "nombre"
    nombre = fields.Char(string='Nombre del Género', required=True)

# -------------------------
# USUARIO (CON VALIDACIÓN DE CÉDULA)
# -------------------------
class Usuario(models.Model):
    _name = "biblioteca.usuario"
    _description = "Usuario de la Biblioteca"
    _rec_name = "nombre_completo"

    nombre_completo = fields.Char("Nombre Completo", required=True)
    cedula = fields.Char("Cédula/DNI", required=True, copy=False)
    telefono = fields.Char("Teléfono")
    email = fields.Char("Email")
    
    prestamo_ids = fields.One2many("biblioteca.prestamo", "usuario_id", string="Préstamos Activos")
    multa_ids = fields.One2many("biblioteca.multa", "usuario_id", string="Multas Pendientes")
    
    # VALIDACIÓN: La cédula debe tener exactamente 10 dígitos.
    @api.constrains('cedula')
    def _validar_cedula(self):
        for registro in self:
            if registro.cedula and not re.match(r'^\d{10}$', registro.cedula):
                raise ValidationError("La cédula/DNI debe tener exactamente 10 dígitos.")
                
    _sql_constraints = [
        ('cedula_uniq', 'unique(cedula)', '¡Ya existe un usuario con esa Cédula/DNI!'),
    ]

# -------------------------
# LIBRO (CON INVENTARIO Y CONEXIÓN)
# -------------------------
class Libro(models.Model):
    _name = 'biblioteca.libro'
    _description = 'Libro'
    _order = "nombre"

    nombre = fields.Char(string='Título', required=True, index=True)
    autor_id = fields.Many2one('biblioteca.autor', string='Autor Principal', required=True)
    genero_ids = fields.Many2many('biblioteca.genero', string='Géneros')
    isbn = fields.Char(string='ISBN')
    descripcion = fields.Text(string="Descripción")

    # Campos de inventario
    copias_totales = fields.Integer(string="Copias Totales", default=1)
    copias_disponibles = fields.Integer(string="Disponibles", compute='_calcular_copias_disponibles', store=True)

    prestamo_ids = fields.One2many('biblioteca.prestamo', 'libro_id', string='Historial de Préstamos')

    @api.depends('prestamo_ids.estado', 'copias_totales')
    def _calcular_copias_disponibles(self):
        for registro in self:
            # Cuenta los préstamos que están 'prestado' o 'vencido'
            prestados = self.env['biblioteca.prestamo'].search_count([
                ('libro_id', '=', registro.id),
                ('estado', 'in', ['prestado', 'vencido'])
            ])
            registro.copias_disponibles = registro.copias_totales - prestados
            
# -------------------------
# PRÉSTAMO
# -------------------------
class Prestamo(models.Model):
    _name = "biblioteca.prestamo"
    _description = "Registro de Préstamo"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    libro_id = fields.Many2one("biblioteca.libro", "Libro", required=True)
    usuario_id = fields.Many2one("biblioteca.usuario", "Usuario", required=True)
    
    fecha_prestamo = fields.Date("Fecha Préstamo", default=fields.Date.context_today)
    dias_prestamo = fields.Integer("Días Prestados", default=15)
    
    fecha_prevista_devolucion = fields.Date(
        "Fecha Prevista", 
        compute='_calcular_fecha_prevista', 
        store=True,
        tracking=True
    )
    fecha_devolucion_real = fields.Date("Fecha Real Devolución")
    
    estado = fields.Selection([
        ('prestado', 'Prestado'),
        ('devuelto', 'Devuelto'),
        ('vencido', 'Vencido'),
    ], default='prestado', string="Estado", tracking=True)
    
    multa_id = fields.Many2one('biblioteca.multa', string='Multa Asociada', readonly=True)
    
    @api.depends('fecha_prestamo', 'dias_prestamo')
    def _calcular_fecha_prevista(self):
        for registro in self:
            if registro.fecha_prestamo and registro.dias_prestamo > 0:
                registro.fecha_prevista_devolucion = registro.fecha_prestamo + timedelta(days=registro.dias_prestamo)
            else:
                registro.fecha_prevista_devolucion = False

    def accion_devolver_libro(self):
        for r in self:
            if r.estado == 'devuelto':
                continue
            
            r.fecha_devolucion_real = fields.Date.context_today(self)
            r.estado = "devuelto"
            
            # Lógica para crear la multa si hay retraso
            if r.fecha_devolucion_real > r.fecha_prevista_devolucion:
                dias_retraso = (r.fecha_devolucion_real - r.fecha_prevista_devolucion).days
                if dias_retraso > 0 and not r.multa_id:
                    multa = self.env["biblioteca.multa"].create({
                        "prestamo_id": r.id,
                        "usuario_id": r.usuario_id.id,
                        "dias_retraso": dias_retraso,
                    })
                    r.multa_id = multa.id

# -------------------------
# MULTA
# -------------------------
class Multa(models.Model):
    _name = "biblioteca.multa"
    _description = "Registro de Multa"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    prestamo_id = fields.Many2one("biblioteca.prestamo", "Préstamo Asociado", required=True, ondelete="cascade")
    usuario_id = fields.Many2one("biblioteca.usuario", "Usuario", required=True)
    
    tarifa_por_dia = fields.Float("Tarifa por día", default=0.5, readonly=True)
    dias_retraso = fields.Integer("Días de Retraso")
    
    monto = fields.Float("Monto Total ($)", compute="_calcular_monto", store=True)
    pagada = fields.Boolean("Pagada", default=False, tracking=True)
    fecha = fields.Date("Fecha Multa", default=fields.Date.context_today)
    
    @api.depends('tarifa_por_dia', 'dias_retraso')
    def _calcular_monto(self):
        for registro in self:
            registro.monto = registro.tarifa_por_dia * registro.dias_retraso

    def accion_marcar_pagada(self):
        for registro in self:
            registro.pagada = True