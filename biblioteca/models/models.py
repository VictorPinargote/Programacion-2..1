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


# ============================================================================
# CAMBIO 1: Clase BibliotecaLibro - AGREGADO CAMPO DE ESTADO
# ============================================================================
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

    # *** NUEVO CAMPO: Estado del Libro ***
    estado_libro = fields.Selection([
        ('disponible', 'Disponible'),
        ('prestado', 'Prestado'),
        ('no_disponible', 'No Disponible'),
        ('en_reparacion', 'En Reparación')
    ], string='Estado del Libro', default='disponible', required=True, 
       help='Estado actual del libro en la biblioteca')

    prestamo_ids = fields.One2many('biblioteca.prestamo', 'libro_id', string='Historial de Préstamos')

    # *** NUEVO CAMPO COMPUTADO: Contadores de préstamos activos ***
    prestamos_activos = fields.Integer(string='Préstamos Activos', 
                                       compute='_compute_prestamos_activos', 
                                       store=True)

    @api.depends('prestamo_ids', 'prestamo_ids.estado')
    def _compute_prestamos_activos(self):
        """Cuenta cuántos préstamos activos tiene el libro"""
        for record in self:
            record.prestamos_activos = len(record.prestamo_ids.filtered(
                lambda p: p.estado in ['p', 'm']
            ))

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
    _rec_name = 'name'

    name = fields.Char(string='Nombre Completo', required=True)
    cedula = fields.Char(string='Cédula', size=10)
    email = fields.Char(string='Email')
    phone = fields.Char(string='Teléfono')
    
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
            if record.cedula:
                if not record.cedula.isdigit():
                    raise ValidationError("La cédula debe contener solo números.")
                
                if len(record.cedula) != 10:
                    raise ValidationError("La cédula debe tener exactamente 10 dígitos.")
                
                provincia = int(record.cedula[0:2])
                if provincia < 1 or provincia > 24:
                    raise ValidationError(f"Código de provincia inválido: {provincia}. Debe estar entre 01 y 24.")
                
                if not self._validar_cedula_ec(record.cedula):
                    raise ValidationError(f"Cédula ecuatoriana inválida: {record.cedula}")

    def _validar_cedula_ec(self, cedula):
        """Validación completa de cédula ecuatoriana"""
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
    dias_prestamo = fields.Integer(string='Días de Préstamo', default=7, required=True,
                                   help='Número de días permitidos para el préstamo de un libro')
    dias_gracia_notificacion = fields.Integer(string='Días de Gracia para Notificación', default=1, required=True,
                                              help='Días después del vencimiento antes de enviar correo de multa')
    monto_multa_dia = fields.Float(string='Monto de Multa por Día', default=1.0, required=True,
                                   help='Monto en dólares que se cobra por cada día de retraso')
    
    # *** NUEVOS CAMPOS: Montos de multa por tipo ***
    monto_multa_dano_leve = fields.Float(string='Multa por Daño Leve', default=5.0, required=True,
                                         help='Monto por daños menores (páginas dobladas, cubiertas rayadas)')
    monto_multa_dano_grave = fields.Float(string='Multa por Daño Grave', default=15.0, required=True,
                                          help='Monto por daños graves (páginas arrancadas, líquidos)')
    monto_multa_perdida = fields.Float(string='Multa por Pérdida', default=50.0, required=True,
                                       help='Monto cuando el libro se pierde completamente')
    
    email_biblioteca = fields.Char(string='Email de la Biblioteca', 
                                   default='biblioteca@ejemplo.com',
                                   help='Email desde el cual se enviarán las notificaciones')

    @api.model
    def get_config(self):
        """Obtiene la configuración activa o crea una por defecto"""
        config = self.search([], limit=1)
        if not config:
            config = self.create({
                'name': 'Configuración de Biblioteca',
                'dias_prestamo': 7,
                'dias_gracia_notificacion': 1,
                'monto_multa_dia': 1.0,
                'monto_multa_dano_leve': 5.0,
                'monto_multa_dano_grave': 15.0,
                'monto_multa_perdida': 50.0,
                'email_biblioteca': 'biblioteca@ejemplo.com'
            })
        return config


# ============================================================================
# CAMBIO 2: Clase BibliotecaPrestamo - MODIFICADO PARA SOPORTAR ESTADOS DE LIBRO
# ============================================================================
class BibliotecaPrestamo(models.Model):
    _name = 'biblioteca.prestamo'
    _description = 'Registro de Préstamo de Libro'
    _rec_name = 'name'

    name = fields.Char(string='Prestamo', required=True, copy=False)
    fecha_prestamo = fields.Datetime(default=fields.Datetime.now, string='Fecha de Préstamo')
    libro_id = fields.Many2one('biblioteca.libro', string='Libro', required=True)
    usuario_id = fields.Many2one('biblioteca.usuario', string='Usuario', required=True)
    email_lector = fields.Char(string='Email del Lector', related='usuario_id.email', store=True, readonly=True)
    fecha_devolucion = fields.Datetime(string='Fecha de Devolución')
    multa_bol = fields.Boolean(default=False, string='Tiene Multa')
    multa = fields.Float(string='Monto Multa', readonly=True)
    fecha_maxima = fields.Datetime(compute='_compute_fecha_maxima', store=True, string='Fecha Máxima de Devolución')
    usuario = fields.Many2one('res.users', string='Usuario presta', default=lambda self: self.env.uid)
    dias_retraso = fields.Integer(string='Días de Retraso', compute='_compute_dias_retraso', store=True)
    notificacion_enviada = fields.Boolean(string='Notificación Enviada', default=False)
    fecha_notificacion = fields.Datetime(string='Fecha de Notificación', readonly=True)

    # *** NUEVO CAMPO: Estado de devolución del libro ***
    condicion_devolucion = fields.Selection([
        ('bueno', 'Buen Estado'),
        ('dano_leve', 'Daño Leve'),
        ('dano_grave', 'Daño Grave'),
        ('perdido', 'Perdido')
    ], string='Condición al Devolver', help='Estado del libro al momento de la devolución')

    # *** NUEVO CAMPO: Notas sobre la condición ***
    notas_devolucion = fields.Text(string='Notas de Devolución', 
                                   help='Detalles sobre el estado del libro devuelto')

    estado = fields.Selection([
        ('b', 'Borrador'),
        ('p', 'Prestado'),
        ('m', 'Con Multa'),
        ('d', 'Devuelto')
    ], string='Estado', default='b')

    @api.depends('fecha_prestamo')
    def _compute_fecha_maxima(self):
        config = self.env['biblioteca.configuracion'].get_config()
        for record in self:
            if record.fecha_prestamo:
                record.fecha_maxima = record.fecha_prestamo + timedelta(days=config.dias_prestamo)
            else:
                record.fecha_maxima = False

    @api.depends('fecha_maxima', 'fecha_devolucion', 'estado')
    def _compute_dias_retraso(self):
        for record in self:
            if record.estado in ['p', 'm'] and record.fecha_maxima:
                fecha_actual = fields.Datetime.now()
                if fecha_actual > record.fecha_maxima:
                    diferencia = fecha_actual - record.fecha_maxima
                    record.dias_retraso = diferencia.days
                else:
                    record.dias_retraso = 0
            elif record.estado == 'd' and record.fecha_devolucion and record.fecha_maxima:
                if record.fecha_devolucion > record.fecha_maxima:
                    diferencia = record.fecha_devolucion - record.fecha_maxima
                    record.dias_retraso = diferencia.days
                else:
                    record.dias_retraso = 0
            else:
                record.dias_retraso = 0

    @api.model
    def create(self, vals):
        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('biblioteca.prestamo') or '/'
        return super().create(vals)

    # *** MODIFICADO: Validación al crear préstamo ***
    @api.constrains('libro_id')
    def _check_libro_disponible(self):
        """Verifica que el libro esté disponible para préstamo"""
        for record in self:
            if record.libro_id.estado_libro != 'disponible' and record.estado == 'b':
                raise ValidationError(
                    f"El libro '{record.libro_id.titulo}' no está disponible para préstamo.\n"
                    f"Estado actual: {dict(record.libro_id._fields['estado_libro'].selection).get(record.libro_id.estado_libro)}"
                )

    def generar_prestamo(self):
        """Genera el préstamo y cambia el estado del libro a 'prestado'"""
        for rec in self:
            if rec.libro_id.estado_libro != 'disponible':
                raise UserError(f"El libro '{rec.libro_id.titulo}' no está disponible para préstamo.")
            
            # Cambiar estado del libro a prestado
            rec.libro_id.write({'estado_libro': 'prestado'})
            rec.write({'estado': 'p'})
            _logger.info(f"Préstamo {rec.name} generado - Libro {rec.libro_id.titulo} marcado como PRESTADO")

    # *** MODIFICADO COMPLETAMENTE: action_devolver con manejo de condiciones ***
    def action_devolver(self):
        """Registra la devolución y genera multa según condición del libro"""
        for rec in self:
            if not rec.condicion_devolucion:
                raise UserError("Debe seleccionar la condición del libro al devolverlo.")
            
            fecha_devolucion = fields.Datetime.now()
            config = self.env['biblioteca.configuracion'].get_config()
            
            # Calcular días de retraso
            dias_retraso = 0
            if fecha_devolucion > rec.fecha_maxima:
                diferencia = fecha_devolucion - rec.fecha_maxima
                dias_retraso = diferencia.days
            
            # Determinar monto de multa según condición
            monto_multa = 0.0
            tipo_multa = False
            nuevo_estado_libro = 'disponible'
            descripcion_multa = ''
            
            # MULTA POR RETRASO
            if dias_retraso > 0:
                monto_multa += dias_retraso * config.monto_multa_dia
                tipo_multa = 'retraso'
                descripcion_multa = f'Retraso de {dias_retraso} días'
            
            # MULTA POR CONDICIÓN DEL LIBRO
            if rec.condicion_devolucion == 'dano_leve':
                monto_multa += config.monto_multa_dano_leve
                tipo_multa = 'dano_leve' if not tipo_multa else 'retraso_y_dano'
                nuevo_estado_libro = 'en_reparacion'
                descripcion_multa += ' + Daño leve al libro'
                
            elif rec.condicion_devolucion == 'dano_grave':
                monto_multa += config.monto_multa_dano_grave
                tipo_multa = 'dano_grave' if not tipo_multa else 'retraso_y_dano'
                nuevo_estado_libro = 'no_disponible'
                descripcion_multa += ' + Daño grave al libro'
                
            elif rec.condicion_devolucion == 'perdido':
                monto_multa += config.monto_multa_perdida
                tipo_multa = 'perdida'
                nuevo_estado_libro = 'no_disponible'
                descripcion_multa = 'Libro perdido'
            
            # Actualizar estado del libro
            rec.libro_id.write({'estado_libro': nuevo_estado_libro})
            _logger.info(f"Libro {rec.libro_id.titulo} actualizado a estado: {nuevo_estado_libro}")
            
            # Generar multa si hay monto
            if monto_multa > 0:
                self.env['biblioteca.multa'].create({
                    'usuario_id': rec.usuario_id.id,
                    'prestamo_id': rec.id,
                    'monto': monto_multa,
                    'dias_retraso': dias_retraso,
                    'tipo_multa': tipo_multa,
                    'descripcion': descripcion_multa.strip(),
                    'fecha_vencimiento': fecha_devolucion.date() + timedelta(days=30),
                    'state': 'pendiente'
                })
                
                rec.write({
                    'fecha_devolucion': fecha_devolucion,
                    'estado': 'm',
                    'multa_bol': True,
                    'multa': monto_multa
                })
                _logger.info(f"Multa generada: ${monto_multa} - Tipo: {tipo_multa}")
            else:
                rec.write({
                    'fecha_devolucion': fecha_devolucion,
                    'estado': 'd',
                    'multa_bol': False,
                    'multa': 0.0
                })

    @api.model
    def _cron_verificar_prestamos_vencidos(self):
        """CRON JOB: Verifica préstamos vencidos y envía correos"""
        _logger.info("=== INICIANDO VERIFICACIÓN DE PRÉSTAMOS VENCIDOS ===")
        
        config = self.env['biblioteca.configuracion'].get_config()
        fecha_actual = fields.Datetime.now()
        
        prestamos_vencidos = self.search([
            ('estado', '=', 'p'),
            ('fecha_maxima', '<', fecha_actual),
            ('notificacion_enviada', '=', False),
        ])
        
        _logger.info(f"Préstamos vencidos encontrados: {len(prestamos_vencidos)}")
        
        for prestamo in prestamos_vencidos:
            dias_retraso = (fecha_actual - prestamo.fecha_maxima).days
            
            if dias_retraso >= config.dias_gracia_notificacion:
                _logger.info(f"Procesando préstamo {prestamo.name} - Retraso: {dias_retraso} días")
                
                multa = prestamo._generar_multa_automatica(dias_retraso, config)
                
                if prestamo.email_lector:
                    prestamo._enviar_correo_multa(multa, config)
                else:
                    _logger.warning(f"Préstamo {prestamo.name} no tiene email")
                
                prestamo.write({
                    'estado': 'm',
                    'multa_bol': True,
                    'notificacion_enviada': True,
                    'fecha_notificacion': fecha_actual
                })
        
        _logger.info("=== VERIFICACIÓN COMPLETADA ===")

    def _generar_multa_automatica(self, dias_retraso, config):
        """Genera multa automáticamente por retraso"""
        multa_existente = self.env['biblioteca.multa'].search([
            ('prestamo_id', '=', self.id),
            ('tipo_multa', '=', 'retraso')
        ], limit=1)
        
        if multa_existente:
            monto_actualizado = dias_retraso * config.monto_multa_dia
            multa_existente.write({
                'dias_retraso': dias_retraso,
                'monto': monto_actualizado,
                'descripcion': f'Retraso de {dias_retraso} días (actualizado)'
            })
            _logger.info(f"Multa actualizada {multa_existente.name} - Monto: ${monto_actualizado}")
            return multa_existente
        else:
            monto_multa = dias_retraso * config.monto_multa_dia
            fecha_vencimiento = fields.Date.today() + timedelta(days=30)
            
            multa = self.env['biblioteca.multa'].create({
                'usuario_id': self.usuario_id.id,
                'prestamo_id': self.id,
                'monto': monto_multa,
                'dias_retraso': dias_retraso,
                'tipo_multa': 'retraso',
                'descripcion': f'Retraso de {dias_retraso} días',
                'fecha_vencimiento': fecha_vencimiento,
                'state': 'pendiente'
            })
            
            self.write({'multa': monto_multa})
            _logger.info(f"Nueva multa creada {multa.name} - Monto: ${monto_multa}")
            return multa

    def _enviar_correo_multa(self, multa, config):
        """Envía correo al lector"""
        try:
            template = self.env.ref('biblioteca.email_template_notificacion_multa', raise_if_not_found=False)
            
            if not template:
                _logger.error("Plantilla de correo no encontrada")
                return False
            
            template.send_mail(self.id, force_send=True)
            _logger.info(f"Correo enviado a {self.email_lector} para préstamo {self.name}")
            return True
            
        except Exception as e:
            _logger.error(f"Error al enviar correo para préstamo {self.name}: {str(e)}")
            return False


# ============================================================================
# CAMBIO 3: Clase BibliotecaMulta - AGREGADO TIPO DE MULTA Y DESCRIPCIÓN
# ============================================================================
class BibliotecaMulta(models.Model):
    _name = 'biblioteca.multa'
    _description = 'Multa por Retraso de Libro'
    _rec_name = 'name'

    name = fields.Char(string='Referencia de Multa', 
                      default=lambda self: self.env['ir.sequence'].next_by_code('biblioteca.multa'), 
                      readonly=True)
    usuario_id = fields.Many2one('biblioteca.usuario', string='Lector Multado', required=True)
    prestamo_id = fields.Many2one('biblioteca.prestamo', string='Préstamo Origen', required=True, ondelete='restrict')
    monto = fields.Float(string='Monto de la Multa', required=True)
    dias_retraso = fields.Integer(string='Días de Retraso', required=True)
    fecha_vencimiento = fields.Date(string='Fecha de Vencimiento', required=True)

    # *** NUEVO CAMPO: Tipo de multa ***
    tipo_multa = fields.Selection([
        ('retraso', 'Por Retraso'),
        ('dano_leve', 'Por Daño Leve'),
        ('dano_grave', 'Por Daño Grave'),
        ('perdida', 'Por Pérdida'),
        ('retraso_y_dano', 'Por Retraso y Daño')
    ], string='Tipo de Multa', required=True, default='retraso',
       help='Clasificación del motivo de la multa')

    # *** NUEVO CAMPO: Descripción detallada ***
    descripcion = fields.Text(string='Descripción', 
                              help='Detalles sobre el motivo de la multa')

    state = fields.Selection([
        ('pendiente', 'Pendiente'),
        ('pagada', 'Pagada'),
        ('cancelada', 'Cancelada')
    ], string='Estado', default='pendiente', required=True)

    def action_pagar(self):
        """Registra el pago de la multa y actualiza estados"""
        self.ensure_one()
        self.state = 'pagada'
        
        # Si el libro está en reparación y la multa se pagó, puede volver a disponible
        if self.prestamo_id.libro_id.estado_libro == 'en_reparacion':
            self.prestamo_id.libro_id.write({'estado_libro': 'disponible'})
            _logger.info(f"Libro {self.prestamo_id.libro_id.titulo} restaurado a DISPONIBLE tras pago de multa")
        
        # Si el préstamo está devuelto, cambiar su estado
        if self.prestamo_id.fecha_devolucion:
            self.prestamo_id.write({'estado': 'd'})
        
        _logger.info(f"Multa {self.name} marcada como pagada")