# -*- coding: utf-8 -*-

import requests
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


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
    _inherits = {'res.partner': 'partner_id'}

    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade', string='Contacto')
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


class BibliotecaConfiguracion(models.Model):
    """Configuración global del sistema de multas"""
    _name = 'biblioteca.configuracion'
    _description = 'Configuración de Multas y Notificaciones'

    name = fields.Char(string='Nombre', default='Configuración de Biblioteca', required=True)
    dias_prestamo = fields.Integer(string='Días de Préstamo', default=2, required=True,
                                   help='Número de días permitidos para el préstamo de un libro')
    dias_gracia_notificacion = fields.Integer(string='Días de Gracia para Notificación', default=1, required=True,
                                              help='Días después del vencimiento antes de enviar correo de multa')
    monto_multa_dia = fields.Float(string='Monto de Multa por Día', default=1.0, required=True,
                                   help='Monto en dólares que se cobra por cada día de retraso')
    email_biblioteca = fields.Char(string='Email de la Biblioteca', 
                                   default='biblioteca@ejemplo.com',
                                   help='Email desde el cual se enviarán las notificaciones')

    _sql_constraints = [
        ('unique_config', 'unique(name)', 'Solo puede existir una configuración activa')
    ]

    @api.model
    def get_config(self):
        """Obtiene la configuración activa o crea una por defecto"""
        config = self.search([], limit=1)
        if not config:
            config = self.create({
                'name': 'Configuración de Biblioteca',
                'dias_prestamo': 2,
                'dias_gracia_notificacion': 1,
                'monto_multa_dia': 1.0,
                'email_biblioteca': 'biblioteca@ejemplo.com'
            })
        return config


class BibliotecaPrestamo(models.Model):
    _name = 'biblioteca.prestamo'
    _description = 'Registro de Préstamo de Libro'
    _rec_name = 'name'

    name = fields.Char(string='Prestamo', required=True, copy=False)
    fecha_prestamo = fields.Datetime(default=fields.Datetime.now)
    libro_id = fields.Many2one('biblioteca.libro', string='Libro', required=True)
    usuario_id = fields.Many2one('biblioteca.usuario', string='Usuario', required=True)
    
    # NUEVO: Campo de email del lector (relacionado)
    email_lector = fields.Char(string='Email del Lector', related='usuario_id.email', store=True, readonly=True)
    
    fecha_devolucion = fields.Datetime()
    multa_bol = fields.Boolean(default=False)
    multa = fields.Float()
    fecha_maxima = fields.Datetime(compute='_compute_fecha_maxima', store=True)
    usuario = fields.Many2one('res.users', string='Usuario presta', default=lambda self: self.env.uid)

    estado = fields.Selection([
        ('b', 'Borrador'), 
        ('p', 'Prestado'), 
        ('m', 'Multa'), 
        ('d', 'Devuelto')
    ], string='Estado', default='b')

    # NUEVO: Campos para control de notificaciones
    notificacion_enviada = fields.Boolean(string='Notificación Enviada', default=False, 
                                         help='Indica si ya se envió el correo de multa')
    fecha_notificacion = fields.Datetime(string='Fecha de Notificación', readonly=True,
                                        help='Fecha y hora en que se envió la notificación de multa')
    dias_retraso = fields.Integer(string='Días de Retraso', compute='_compute_dias_retraso', store=True)

    @api.depends('fecha_prestamo')
    def _compute_fecha_maxima(self):
        """Calcula la fecha máxima de devolución basada en la configuración"""
        config = self.env['biblioteca.configuracion'].get_config()
        for record in self:
            if record.fecha_prestamo:
                record.fecha_maxima = record.fecha_prestamo + timedelta(days=config.dias_prestamo)
            else:
                record.fecha_maxima = False

    @api.depends('fecha_maxima', 'fecha_devolucion', 'estado')
    def _compute_dias_retraso(self):
        """Calcula los días de retraso si el libro no se ha devuelto"""
        for record in self:
            if record.estado in ['p', 'm'] and record.fecha_maxima:
                fecha_comparacion = record.fecha_devolucion or fields.Datetime.now()
                if fecha_comparacion > record.fecha_maxima:
                    delta = fecha_comparacion - record.fecha_maxima
                    record.dias_retraso = delta.days
                else:
                    record.dias_retraso = 0
            else:
                record.dias_retraso = 0

    @api.model
    def create(self, vals):
        """Genera automáticamente el código del préstamo"""
        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('biblioteca.prestamo') or '/'
        return super().create(vals)

    def generar_prestamo(self):
        """Cambia el estado a 'prestado'"""
        for rec in self:
            rec.write({'estado': 'p'})

    @api.model
    def _cron_verificar_prestamos_vencidos(self):
        """
        CRON JOB: Verifica préstamos vencidos y envía correos automáticos
        
        Este método se ejecuta automáticamente según la configuración del cron.
        Busca préstamos que:
        1. Estén en estado 'prestado' (p)
        2. Hayan superado la fecha máxima de devolución
        3. Cumplan con los días de gracia configurados
        4. No tengan notificación enviada
        """
        _logger.info("=== INICIANDO VERIFICACIÓN DE PRÉSTAMOS VENCIDOS ===")
        
        # Obtener configuración
        config = self.env['biblioteca.configuracion'].get_config()
        fecha_actual = fields.Datetime.now()
        
        # Buscar préstamos vencidos que no han sido notificados
        prestamos_vencidos = self.search([
            ('estado', '=', 'p'),  # Solo préstamos activos
            ('fecha_maxima', '<', fecha_actual),  # Ya pasó la fecha máxima
            ('notificacion_enviada', '=', False),  # No se ha enviado notificación
        ])
        
        _logger.info(f"Préstamos vencidos encontrados: {len(prestamos_vencidos)}")
        
        for prestamo in prestamos_vencidos:
            # Calcular días de retraso
            dias_retraso = (fecha_actual - prestamo.fecha_maxima).days
            
            # Verificar si cumple con los días de gracia
            if dias_retraso >= config.dias_gracia_notificacion:
                _logger.info(f"Procesando préstamo {prestamo.name} - Retraso: {dias_retraso} días")
                
                # Crear o actualizar multa
                multa = prestamo._generar_multa_automatica(dias_retraso, config)
                
                # Enviar correo de notificación
                if prestamo.email_lector:
                    prestamo._enviar_correo_multa(multa, config)
                else:
                    _logger.warning(f"Préstamo {prestamo.name} no tiene email del lector configurado")
                
                # Actualizar estado del préstamo
                prestamo.write({
                    'estado': 'm',
                    'multa_bol': True,
                    'notificacion_enviada': True,
                    'fecha_notificacion': fecha_actual
                })
        
        _logger.info("=== VERIFICACIÓN COMPLETADA ===")

    def _generar_multa_automatica(self, dias_retraso, config):
        """
        Genera automáticamente una multa para el préstamo
        
        Args:
            dias_retraso: Número de días de retraso
            config: Objeto de configuración con el monto por día
        
        Returns:
            Objeto multa creado o existente
        """
        # Verificar si ya existe una multa para este préstamo
        multa_existente = self.env['biblioteca.multa'].search([
            ('prestamo_id', '=', self.id)
        ], limit=1)
        
        if multa_existente:
            # Actualizar multa existente
            monto_actualizado = dias_retraso * config.monto_multa_dia
            multa_existente.write({
                'dias_retraso': dias_retraso,
                'monto': monto_actualizado
            })
            _logger.info(f"Multa actualizada {multa_existente.name} - Nuevo monto: ${monto_actualizado}")
            return multa_existente
        else:
            # Crear nueva multa
            monto_multa = dias_retraso * config.monto_multa_dia
            fecha_vencimiento = fields.Date.today() + timedelta(days=30)
            
            multa = self.env['biblioteca.multa'].create({
                'usuario_id': self.usuario_id.id,
                'prestamo_id': self.id,
                'monto': monto_multa,
                'dias_retraso': dias_retraso,
                'fecha_vencimiento': fecha_vencimiento,
                'state': 'pendiente'
            })
            
            # Actualizar campo multa en el préstamo
            self.write({'multa': monto_multa})
            
            _logger.info(f"Nueva multa creada {multa.name} - Monto: ${monto_multa}")
            return multa

    def _enviar_correo_multa(self, multa, config):
        """
        Envía correo electrónico al lector notificando la multa
        
        Args:
            multa: Objeto multa generada
            config: Configuración del sistema
        """
        try:
            # Obtener la plantilla de correo
            template = self.env.ref('biblioteca.email_template_notificacion_multa', raise_if_not_found=False)
            
            if not template:
                _logger.error("Plantilla de correo 'email_template_notificacion_multa' no encontrada")
                return False
            
            # Preparar contexto para la plantilla
            ctx = {
                'prestamo': self,
                'multa': multa,
                'config': config,
                'lector_nombre': self.usuario_id.name,
                'libro_titulo': self.libro_id.titulo,
                'dias_retraso': multa.dias_retraso,
                'monto_multa': multa.monto,
                'fecha_vencimiento': multa.fecha_vencimiento,
            }
            
            # Enviar correo usando la plantilla
            template.with_context(ctx).send_mail(self.id, force_send=True)
            
            _logger.info(f"Correo enviado exitosamente a {self.email_lector} para préstamo {self.name}")
            return True
            
        except Exception as e:
            _logger.error(f"Error al enviar correo para préstamo {self.name}: {str(e)}")
            return False


class BibliotecaMulta(models.Model):
    _name = 'biblioteca.multa'
    _description = 'Multa por Retraso de Libro'
    _rec_name = 'name'

    name = fields.Char(string='Referencia de Multa', 
                      default=lambda self: self.env['ir.sequence'].next_by_code('biblioteca.multa'), 
                      readonly=True)
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
        """Marca la multa como pagada y actualiza el estado del préstamo"""
        self.ensure_one()
        self.state = 'pagada'
        
        # Si se paga la multa y el libro ya fue devuelto, cambiar estado a 'devuelto'
        if self.prestamo_id.fecha_devolucion:
            self.prestamo_id.write({'estado': 'd'})
        
        _logger.info(f"Multa {self.name} marcada como pagada")