# -*- coding: utf-8 -*-

import requests
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta


class BibliotecaAutor(models.Model):
    _name = 'biblioteca.autor'
    _description = 'Autor de la Biblioteca'
    _rec_name = 'display_name'

    firstname = fields.Char(string='Nombre')
    lastname = fields.Char(string='Apellido')
    nacimiento = fields.Date()
    display_name = fields.Char(compute='_compute_display_name', store=True)
    libro_ids = fields.One2many('biblioteca.libro', 'autor', string='Libros Escritos')

    @api.depends('firstname', 'lastname')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.firstname or ''} {record.lastname or ''}".strip()


class BibliotecaEditorial(models.Model):
    _name = 'biblioteca.editorial'
    _description = 'Editorial de libros'

    name = fields.Char(string='Nombre Editorial', required=True)
    pais = fields.Char(string='País')
    ciudad = fields.Char(string='Ciudad')


class BibliotecaLibro(models.Model):
    _name = 'biblioteca.libro'
    _description = 'Libro de la Biblioteca'
    _rec_name = 'titulo'

    firstname = fields.Char(string='Nombre de búsqueda')
    titulo = fields.Char(string='Título del Libro')
    autor = fields.Many2one('biblioteca.autor', string='Autor')
    ejemplares = fields.Integer(string='Número de ejemplares', default=1)
    costo = fields.Float(string='Costo')
    description = fields.Text(string='Resumen del libro')
    fecha_publicacion = fields.Date(string='Fecha de Publicación')
    genero = fields.Char(string='Género')
    isbn = fields.Char(string='ISBN')
    paginas = fields.Integer(string='Páginas')
    editorial = fields.Many2one('biblioteca.editorial', string='Editorial')
    ubicacion = fields.Char(string='Categoría')

    prestamo_ids = fields.One2many('biblioteca.prestamo', 'libro_id', string='Historial de Préstamos')

    def action_buscar_openlibrary(self):
        for record in self:
            if not record.firstname:
                raise UserError("Por favor, ingrese un nombre en 'Nombre de búsqueda' antes de buscar en OpenLibrary.")
            try:
                url = f"https://openlibrary.org/search.json?q={record.firstname}&language=spa"
                response = requests.get(url, timeout=8)
                response.raise_for_status()
                data = response.json()
                if not data.get('docs'):
                    raise UserError("No se encontró ningún libro con ese nombre en OpenLibrary.")
                libro = data['docs'][0]
                work_key = libro.get('key')
                titulo = libro.get('title', 'Sin título')
                autor_nombre = libro.get('author_name', ['Desconocido'])[0]
                anio = libro.get('first_publish_year')
                editorial_nombre = libro.get('publisher', ['Desconocido'])[0]
                paginas = 0
                descripcion = ''
                generos = []
                isbn = libro.get('isbn', [None])[0] if libro.get('isbn') else None

                if work_key:
                    work_url = f"https://openlibrary.org{work_key}.json"
                    work_resp = requests.get(work_url, timeout=10)
                    if work_resp.ok:
                        work_data = work_resp.json()
                        if isinstance(work_data.get('description'), dict):
                            descripcion = work_data['description'].get('value', '')
                        elif isinstance(work_data.get('description'), str):
                            descripcion = work_data['description']
                        if work_data.get('subjects'):
                            generos = work_data['subjects'][:3]
                        editions_url = f"https://openlibrary.org{work_key}/editions.json"
                        editions_resp = requests.get(editions_url, timeout=10)
                        if editions_resp.ok:
                            editions_data = editions_resp.json()
                            if editions_data.get('entries'):
                                entry = editions_data['entries'][0]
                                paginas = entry.get('number_of_pages', 0)
                                isbn = entry.get('isbn_10', [None])[0] if entry.get('isbn_10') else isbn
                                editorial_nombre = entry.get('publishers', [None])[0] if entry.get('publishers') else editorial_nombre

                autor = self.env['biblioteca.autor'].search([('firstname', '=', autor_nombre)], limit=1)
                if not autor:
                    autor = self.env['biblioteca.autor'].create({'firstname': autor_nombre})
                editorial = self.env['biblioteca.editorial'].search([('name', '=', editorial_nombre)], limit=1)
                if not editorial:
                    editorial = self.env['biblioteca.editorial'].create({'name': editorial_nombre})

                record.write({
                    'titulo': titulo,
                    'autor': autor.id,
                    'isbn': isbn or 'No disponible',
                    'paginas': paginas or 0,
                    'fecha_publicacion': datetime.strptime(str(anio), '%Y').date() if anio else None,
                    'description': descripcion or 'No hay descripción disponible.',
                    'editorial': editorial.id,
                    'genero': ', '.join(generos) if generos else 'Desconocido',
                })
            except Exception as e:
                raise UserError(f"Error al conectar con OpenLibrary: {str(e)}")


class BibliotecaUsuario(models.Model):
    _name = 'biblioteca.usuario'
    _description = 'Usuario/Lector de la Biblioteca'
    _inherit = ['res.partner']

    cedula = fields.Char(string='Cédula')
    prestamo_ids = fields.One2many('biblioteca.prestamo', 'usuario_id', string='Préstamos Realizados')
    multa_ids = fields.One2many('biblioteca.multa', 'usuario_id', string='Multas')

    prestamo_count = fields.Integer(string='Número de Préstamos', compute='_compute_prestamo_count', store=True)
    multa_pendiente_count = fields.Integer(string='Multas Pendientes', compute='_compute_multa_pendiente_count', store=True)

    @api.depends('prestamo_ids')
    def _compute_prestamo_count(self):
        for record in self:
            record.prestamo_count = len(record.prestamo_ids)

    @api.depends('multa_ids.state')
    def _compute_multa_pendiente_count(self):
        for record in self:
            record.multa_pendiente_count = len(record.multa_ids.filtered(lambda m: m.state == 'pendiente'))

    @api.constrains('cedula')
    def _check_cedula(self):
        for record in self:
            if record.cedula and not self._validar_cedula_ec(record.cedula):
                raise ValidationError(f"Cédula ecuatoriana inválida: {record.cedula}")

    def _validar_cedula_ec(self, cedula):
        if len(cedula) != 10 or not cedula.isdigit():
            return False
        provincia = int(cedula[0:2])
        if provincia < 1 or provincia > 24:
            return False
        coef = [2, 1, 2, 1, 2, 1, 2, 1, 2]
        total = 0
        for i in range(9):
            val = int(cedula[i]) * coef[i]
            if val >= 10:
                val -= 9
            total += val
        digito_verificador = 10 - (total % 10) if total % 10 != 0 else 0
        return digito_verificador == int(cedula[9])


class BibliotecaPersonal(models.Model):
    _name = 'biblioteca.personal'
    _description = 'Personal de la biblioteca'

    name = fields.Char(string='Nombre Completo', required=True)
    cargo = fields.Char(string='Cargo')
    telefono = fields.Char(string='Teléfono')
    email = fields.Char(string='Email')


class BibliotecaPrestamo(models.Model):
    _name = 'biblioteca.prestamo'
    _description = 'Registro de Préstamo de Libro'
    _rec_name = 'name'

    name = fields.Char(string='Prestamo', required=True, copy=False)
    fecha_prestamo = fields.Datetime(default=fields.Datetime.now)
    libro_id = fields.Many2one('biblioteca.libro', string='Libro')
    usuario_id = fields.Many2one('biblioteca.usuario', string='Usuario')
    fecha_devolucion = fields.Datetime()
    multa_bol = fields.Boolean(default=False)
    multa = fields.Float()
    fecha_maxima = fields.Datetime(compute='_compute_fecha_maxima', store=True)
    usuario = fields.Many2one('res.users', string='Usuario presta', default=lambda self: self.env.uid)

    estado = fields.Selection([('b', 'Borrador'), ('p', 'Prestado'), ('m', 'Multa'), ('d', 'Devuelto')], string='Estado', default='b')

    @api.depends('fecha_prestamo')
    def _compute_fecha_maxima(self):
        for record in self:
            record.fecha_maxima = record.fecha_prestamo + timedelta(days=2) if record.fecha_prestamo else False

    @api.model
    def create(self, vals):
        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('biblioteca.prestamo') or '/'
        return super().create(vals)

    def generar_prestamo(self):
        for rec in self:
            rec.write({'estado': 'p'})


class BibliotecaMulta(models.Model):
    _name = 'biblioteca.multa'
    _description = 'Multa por Retraso de Libro'
    _rec_name = 'name'

    name = fields.Char(string='Referencia de Multa', default=lambda self: self.env['ir.sequence'].next_by_code('biblioteca.multa'), readonly=True)
    usuario_id = fields.Many2one('biblioteca.usuario', string='Lector Multado', required=True)
    prestamo_id = fields.Many2one('biblioteca.prestamo', string='Préstamo Origen', required=True, ondelete='restrict')
    monto = fields.Float(string='Monto de la Multa', required=True, digits='Product Price')
    dias_retraso = fields.Integer(string='Días de Retraso', required=True)
    fecha_vencimiento = fields.Date(string='Fecha de Vencimiento', required=True)

    state = fields.Selection([
        ('pendiente', 'Pendiente'),
        ('pagada', 'Pagada'),
        ('cancelada', 'Cancelada')
    ], string='Estado', default='pendiente', required=True)

    def action_pagar(self):
        self.ensure_one()
        self.state = 'pagada'

