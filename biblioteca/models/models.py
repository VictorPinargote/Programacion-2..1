# -*- coding: utf-8 -*-

import requests
import random
import json
import os
from datetime import datetime, timedelta
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)

# ============================================================================
# CONTRASEÑA MAESTRA PARA CREAR ADMINISTRADORES
# ============================================================================
CONTRASENA_MAESTRA_ADMIN = "Joel1234"

# ============================================================================
# SISTEMA DE ALMACENAMIENTO JSON (INVISIBLE PARA USUARIOS)
# ============================================================================
def get_json_path():
    """Obtiene la ruta del archivo JSON"""
    module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(module_path, 'data', 'biblioteca_backup.json')
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    return json_path

def guardar_en_json(categoria, datos, accion='crear'):
    """
    Guarda/actualiza/elimina datos en JSON automáticamente
    accion: 'crear', 'actualizar', 'eliminar'
    """
    try:
        json_path = get_json_path()
        
        # Leer o crear estructura
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                contenido = json.load(f)
        else:
            contenido = {
                'metadata': {
                    'creado': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'ultima_actualizacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'total_registros': 0
                },
                'contrasenas': {
                    'admin_maestra': CONTRASENA_MAESTRA_ADMIN
                },
                'usuarios_sistema': [],
                'configuracion': {},
                'historial_eliminados': []
            }
        
        # Procesar según categoría y acción
        if categoria == 'usuarios':
            if accion == 'eliminar':
                # Mover a historial de eliminados
                for i, u in enumerate(contenido['usuarios_sistema']):
                    if u.get('login') == datos.get('login'):
                        usuario_eliminado = contenido['usuarios_sistema'].pop(i)
                        usuario_eliminado['fecha_eliminacion'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        usuario_eliminado['estado'] = '❌ ELIMINADO'
                        contenido['historial_eliminados'].append(usuario_eliminado)
                        break
            else:
                # Crear o actualizar
                usuario_existente = False
                for i, u in enumerate(contenido['usuarios_sistema']):
                    if u.get('login') == datos.get('login'):
                        contenido['usuarios_sistema'][i] = datos
                        usuario_existente = True
                        break
                if not usuario_existente:
                    contenido['usuarios_sistema'].append(datos)
        
        elif categoria == 'configuracion':
            contenido['configuracion'] = datos
        
        # Actualizar metadata
        contenido['metadata']['ultima_actualizacion'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        contenido['metadata']['total_registros'] = len(contenido['usuarios_sistema'])
        
        # Guardar
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(contenido, f, indent=4, ensure_ascii=False)
        
        _logger.info(f"✅ JSON actualizado - Categoría: {categoria}, Acción: {accion}")
        return True
        
    except Exception as e:
        _logger.error(f"❌ Error al guardar en JSON: {str(e)}")
        return False


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
    ejemplares = fields.Integer(string='Copias Totales', default=1)
    copias_disponibles = fields.Integer(string='Copias Disponibles', compute='_compute_copias_disponibles', store=True)
    copias_prestadas = fields.Integer(string='Copias Prestadas', compute='_compute_copias_disponibles', store=True)
    costo = fields.Float(string='Costo')
    description = fields.Text(string='Resumen del libro')
    fecha_publicacion = fields.Date(string='Fecha de Publicación')
    genero = fields.Char(string='Género')
    isbn = fields.Char(string='ISBN')
    paginas = fields.Integer(string='Páginas')
    editorial = fields.Many2one('biblioteca.editorial', string='Editorial')
    ubicacion = fields.Char(string='Categoría')
    estado_libro = fields.Selection([
        ('disponible', 'Disponible'),
        ('prestado', 'Totalmente Prestado'),
        ('no_disponible', 'No Disponible'),
    ], string='Estado del Libro', compute='_compute_estado_libro', store=True)
    prestamo_ids = fields.One2many('biblioteca.prestamo', 'libro_id', string='Historial de Préstamos')
    prestamos_activos = fields.Integer(string='Préstamos Activos', compute='_compute_prestamos_activos', store=True)

    @api.depends('ejemplares', 'prestamo_ids', 'prestamo_ids.estado')
    def _compute_copias_disponibles(self):
        for record in self:
            prestamos_activos = record.prestamo_ids.filtered(lambda p: p.estado in ['p', 'm'])
            record.copias_prestadas = len(prestamos_activos)
            record.copias_disponibles = max(0, record.ejemplares - record.copias_prestadas)

    @api.depends('copias_disponibles', 'ejemplares')
    def _compute_estado_libro(self):
        for record in self:
            if record.ejemplares == 0:
                record.estado_libro = 'no_disponible'
            elif record.copias_disponibles > 0:
                record.estado_libro = 'disponible'
            else:
                record.estado_libro = 'prestado'

    @api.depends('prestamo_ids', 'prestamo_ids.estado')
    def _compute_prestamos_activos(self):
        for record in self:
            record.prestamos_activos = len(record.prestamo_ids.filtered(lambda p: p.estado in ['p', 'm']))

    def action_buscar_openlibrary(self):
        for record in self:
            if not record.firstname:
                raise UserError("Por favor, ingrese un nombre en 'Nombre de búsqueda'.")
            try:
                url = f"https://openlibrary.org/search.json?q={record.firstname}&language=spa"
                response = requests.get(url, timeout=8)
                response.raise_for_status()
                data = response.json()
                if not data.get('docs'):
                    raise UserError("No se encontró ningún libro.")
                
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
                num_ediciones = libro.get('edition_count', 0)
                ejemplares_sugeridos = self._calcular_ejemplares_desde_ediciones(num_ediciones)

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
                    'ejemplares': ejemplares_sugeridos,
                })
                
            except Exception as e:
                raise UserError(f"Error al conectar con OpenLibrary: {str(e)}")

    def _calcular_ejemplares_desde_ediciones(self, num_ediciones):
        if num_ediciones == 0:
            return random.randint(1, 3)
        elif num_ediciones < 5:
            return random.randint(1, 2)
        elif num_ediciones < 20:
            return random.randint(2, 5)
        elif num_ediciones < 50:
            return random.randint(5, 10)
        else:
            return random.randint(10, 20)


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
                    raise ValidationError(f"Código de provincia inválido: {provincia}.")
                if not self._validar_cedula_ec(record.cedula):
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


# ============================================================================
# USUARIOS DEL SISTEMA CON GUARDADO AUTOMÁTICO EN JSON (SIN BOTONES)
# ============================================================================
class BibliotecaUsuarioSistema(models.Model):
    _name = 'biblioteca.usuario.sistema'
    _description = 'Gestión de Usuarios del Sistema'

    name = fields.Char(string='Nombre Completo', required=True)
    login = fields.Char(string='Usuario (Login)', required=True)
    password = fields.Char(string='Contraseña', required=True)
    email = fields.Char(string='Email')
    es_administrador = fields.Boolean(string='Es Administrador', default=False)
    contrasena_admin = fields.Char(string='Contraseña de Administrador')
    user_id = fields.Many2one('res.users', string='Usuario Creado', readonly=True)

    @api.model
    def create(self, vals):
        """Sobrescribir create para guardar en JSON automáticamente"""
        res = super().create(vals)
        
        # Guardar en JSON al crear
        guardar_en_json('usuarios', {
            'id': res.id,
            'nombre': res.name,
            'login': res.login,
            'password': res.password,
            'email': res.email or f"{res.login}@biblioteca.com",
            'tipo': 'Usuario Normal' if not res.es_administrador else '🔐 ADMINISTRADOR',
            'fecha_creacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'estado': '✅ ACTIVO'
        }, accion='crear')
        
        return res

    def write(self, vals):
        """Sobrescribir write para actualizar JSON automáticamente"""
        res = super().write(vals)
        
        # Actualizar en JSON
        for record in self:
            guardar_en_json('usuarios', {
                'id': record.id,
                'nombre': record.name,
                'login': record.login,
                'password': record.password,
                'email': record.email or f"{record.login}@biblioteca.com",
                'tipo': 'Usuario Normal' if not record.es_administrador else '🔐 ADMINISTRADOR',
                'fecha_creacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'ultima_modificacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'estado': '✅ ACTIVO'
            }, accion='actualizar')
        
        return res

    def unlink(self):
        """Sobrescribir unlink para mover a historial de eliminados en JSON"""
        for record in self:
            guardar_en_json('usuarios', {
                'id': record.id,
                'nombre': record.name,
                'login': record.login,
                'password': record.password,
                'email': record.email,
                'tipo': 'Usuario Normal' if not record.es_administrador else '🔐 ADMINISTRADOR'
            }, accion='eliminar')
        
        return super().unlink()

    def action_crear_usuario_normal(self):
        for record in self:
            existing_user = self.env['res.users'].sudo().search([('login', '=', record.login)], limit=1)
            if existing_user:
                raise UserError(f"El usuario '{record.login}' ya existe.")
            
            try:
                grupo_usuario = self.env.ref('biblioteca.group_biblioteca_usuario')
                nuevo_usuario = self.env['res.users'].sudo().create({
                    'name': record.name,
                    'login': record.login,
                    'password': record.password,
                    'email': record.email or f"{record.login}@biblioteca.com",
                    'groups_id': [(6, 0, [grupo_usuario.id])]
                })
                
                record.write({'user_id': nuevo_usuario.id, 'es_administrador': False})
                _logger.info(f"✅ Usuario normal creado: {record.login}")
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': '✅ Usuario Creado',
                        'message': f'Usuario normal "{record.name}" creado exitosamente.',
                        'type': 'success',
                        'sticky': False,
                    }
                }
            except Exception as e:
                raise UserError(f"Error al crear usuario: {str(e)}")

    def action_crear_administrador(self):
        for record in self:
            if not record.contrasena_admin:
                raise UserError("Debe ingresar la contraseña de administrador.")
            if record.contrasena_admin != CONTRASENA_MAESTRA_ADMIN:
                raise UserError("❌ Contraseña de administrador incorrecta.")
            
            existing_user = self.env['res.users'].sudo().search([('login', '=', record.login)], limit=1)
            if existing_user:
                raise UserError(f"El usuario '{record.login}' ya existe.")
            
            try:
                grupo_admin = self.env.ref('biblioteca.group_biblioteca_administrador')
                nuevo_usuario = self.env['res.users'].sudo().create({
                    'name': record.name,
                    'login': record.login,
                    'password': record.password,
                    'email': record.email or f"{record.login}@biblioteca.com",
                    'groups_id': [(6, 0, [grupo_admin.id])]
                })
                
                record.write({'user_id': nuevo_usuario.id, 'es_administrador': True, 'contrasena_admin': False})
                _logger.info(f"✅ Administrador creado: {record.login}")
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': '✅ Administrador Creado',
                        'message': f'Administrador "{record.name}" creado exitosamente.',
                        'type': 'success',
                        'sticky': False,
                    }
                }
            except Exception as e:
                raise UserError(f"Error al crear administrador: {str(e)}")


class BibliotecaPersonal(models.Model):
    _name = 'biblioteca.personal'
    _description = 'Personal de la biblioteca'

    name = fields.Char(string='Nombre Completo', required=True)
    cargo = fields.Char(string='Cargo')
    telefono = fields.Char(string='Teléfono')
    email = fields.Char(string='Email')


# ============================================================================
# CONFIGURACIÓN CON GUARDADO AUTOMÁTICO EN JSON
# ============================================================================
class BibliotecaConfiguracion(models.Model):
    _name = 'biblioteca.configuracion'
    _description = 'Configuración de Multas y Notificaciones'

    name = fields.Char(string='Nombre', default='Configuración de Biblioteca', required=True)
    dias_prestamo = fields.Integer(string='Días de Préstamo', default=7, required=True)
    dias_gracia_notificacion = fields.Integer(string='Días de Gracia para Notificación', default=1, required=True)
    monto_multa_dia = fields.Float(string='Monto de Multa por Día', default=1.0, required=True)
    monto_multa_dano_leve = fields.Float(string='Multa por Daño Leve', default=5.0, required=True)
    monto_multa_dano_grave = fields.Float(string='Multa por Daño Grave', default=15.0, required=True)
    monto_multa_perdida = fields.Float(string='Multa por Pérdida', default=50.0, required=True)
    email_biblioteca = fields.Char(string='Email de la Biblioteca', default='biblioteca@ejemplo.com')

    @api.model
    def get_config(self):
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

    def write(self, vals):
        """Guardar en JSON automáticamente al modificar configuración"""
        res = super().write(vals)
        
        for record in self:
            guardar_en_json('configuracion', {
                'dias_prestamo': record.dias_prestamo,
                'dias_gracia_notificacion': record.dias_gracia_notificacion,
                'monto_multa_dia': record.monto_multa_dia,
                'monto_multa_dano_leve': record.monto_multa_dano_leve,
                'monto_multa_dano_grave': record.monto_multa_dano_grave,
                'monto_multa_perdida': record.monto_multa_perdida,
                'email_biblioteca': record.email_biblioteca,
                'ultima_modificacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return res


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
    condicion_devolucion = fields.Selection([
        ('bueno', 'Buen Estado'),
        ('dano_leve', 'Daño Leve'),
        ('dano_grave', 'Daño Grave'),
        ('perdido', 'Perdido')
    ], string='Condición al Devolver')
    notas_devolucion = fields.Text(string='Notas de Devolución')
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

    @api.constrains('libro_id', 'estado')
    def _check_copias_disponibles(self):
        for record in self:
            if record.estado == 'b' and record.libro_id:
                if record.libro_id.copias_disponibles <= 0:
                    raise ValidationError(
                        f"No hay copias disponibles del libro '{record.libro_id.titulo}'.\n"
                        f"Copias totales: {record.libro_id.ejemplares}\n"
                        f"Copias prestadas: {record.libro_id.copias_prestadas}"
                    )

    def generar_prestamo(self):
        for rec in self:
            if rec.libro_id.copias_disponibles <= 0:
                raise UserError(f"No hay copias disponibles del libro '{rec.libro_id.titulo}'.")
            rec.write({'estado': 'p'})

    def action_devolver(self):
        for rec in self:
            if not rec.condicion_devolucion:
                raise UserError("Debe seleccionar la condición del libro al devolverlo.")
            
            fecha_devolucion = fields.Datetime.now()
            config = self.env['biblioteca.configuracion'].get_config()
            
            dias_retraso = 0
            if fecha_devolucion > rec.fecha_maxima:
                diferencia = fecha_devolucion - rec.fecha_maxima
                dias_retraso = diferencia.days
            
            monto_multa = 0.0
            tipo_multa = False
            descripcion_multa = ''
            reduce_ejemplares = False
            
            if dias_retraso > 0:
                monto_multa += dias_retraso * config.monto_multa_dia
                tipo_multa = 'retraso'
                descripcion_multa = f'Retraso de {dias_retraso} días'
            
            if rec.condicion_devolucion == 'dano_leve':
                monto_multa += config.monto_multa_dano_leve
                tipo_multa = 'dano_leve' if not tipo_multa else 'retraso_y_dano'
                descripcion_multa += ' + Daño leve al libro'
            elif rec.condicion_devolucion == 'dano_grave':
                monto_multa += config.monto_multa_dano_grave
                tipo_multa = 'dano_grave' if not tipo_multa else 'retraso_y_dano'
                descripcion_multa += ' + Daño grave al libro'
                reduce_ejemplares = True
            elif rec.condicion_devolucion == 'perdido':
                monto_multa += config.monto_multa_perdida
                tipo_multa = 'perdida'
                descripcion_multa = 'Libro perdido'
                reduce_ejemplares = True
            
            if reduce_ejemplares:
                nuevos_ejemplares = max(0, rec.libro_id.ejemplares - 1)
                rec.libro_id.write({'ejemplares': nuevos_ejemplares})
            
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
            else:
                rec.write({
                    'fecha_devolucion': fecha_devolucion,
                    'estado': 'd',
                    'multa_bol': False,
                    'multa': 0.0
                })

    @api.model
    def _cron_verificar_prestamos_vencidos(self):
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
            try:
                dias_retraso = (fecha_actual - prestamo.fecha_maxima).days
                
                if dias_retraso >= config.dias_gracia_notificacion:
                    _logger.info(f"Procesando préstamo {prestamo.name} - Retraso: {dias_retraso} días")
                    
                    multa = prestamo._generar_multa_automatica(dias_retraso, config)
                    
                    if multa:
                        _logger.info(f"✅ Multa creada: {multa.name} - Monto: ${multa.monto}")
                        
                        if prestamo.email_lector:
                            correo_enviado = prestamo._enviar_correo_multa(multa, config)
                            if correo_enviado:
                                _logger.info(f"✅ Correo enviado a {prestamo.email_lector}")
                            else:
                                _logger.warning(f"⚠️ No se pudo enviar correo")
                        else:
                            _logger.warning(f"⚠️ Préstamo {prestamo.name} no tiene email")
                        
                        prestamo.write({
                            'estado': 'm',
                            'multa_bol': True,
                            'multa': multa.monto,
                            'notificacion_enviada': True,
                            'fecha_notificacion': fecha_actual
                        })
                    else:
                        _logger.error(f"❌ No se pudo crear multa para préstamo {prestamo.name}")
                        
            except Exception as e:
                _logger.error(f"❌ Error procesando préstamo {prestamo.name}: {str(e)}")
                continue
        
        _logger.info("=== VERIFICACIÓN COMPLETADA ===")

    def _generar_multa_automatica(self, dias_retraso, config):
        self.ensure_one()
        
        multa_existente = self.env['biblioteca.multa'].search([
            ('prestamo_id', '=', self.id),
            ('tipo_multa', '=', 'retraso'),
            ('state', '=', 'pendiente')
        ], limit=1)
        
        monto_actualizado = dias_retraso * config.monto_multa_dia
        fecha_vencimiento = fields.Date.today() + timedelta(days=30)
        
        if multa_existente:
            multa_existente.write({
                'dias_retraso': dias_retraso,
                'monto': monto_actualizado,
                'descripcion': f'Retraso de {dias_retraso} días (actualizado automáticamente)',
                'fecha_vencimiento': fecha_vencimiento
            })
            _logger.info(f"Multa ACTUALIZADA: {multa_existente.name}")
            return multa_existente
        else:
            try:
                multa = self.env['biblioteca.multa'].create({
                    'usuario_id': self.usuario_id.id,
                    'prestamo_id': self.id,
                    'monto': monto_actualizado,
                    'dias_retraso': dias_retraso,
                    'tipo_multa': 'retraso',
                    'descripcion': f'Retraso de {dias_retraso} días (generado automáticamente)',
                    'fecha_vencimiento': fecha_vencimiento,
                    'state': 'pendiente'
                })
                
                _logger.info(f"Multa CREADA: {multa.name} - Monto: ${monto_actualizado}")
                return multa
                
            except Exception as e:
                _logger.error(f"Error al crear multa: {str(e)}")
                return False

    def _enviar_correo_multa(self, multa, config):
        try:
            template = self.env.ref('biblioteca.email_template_notificacion_multa', raise_if_not_found=False)
            
            if not template:
                _logger.error("Plantilla de correo no encontrada")
                return False
            
            template.send_mail(self.id, force_send=True)
            _logger.info(f"Correo enviado exitosamente")
            return True
            
        except Exception as e:
            _logger.error(f"Error al enviar correo: {str(e)}")
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
    monto = fields.Float(string='Monto de la Multa', required=True)
    dias_retraso = fields.Integer(string='Días de Retraso', required=True)
    fecha_vencimiento = fields.Date(string='Fecha de Vencimiento', required=True)
    tipo_multa = fields.Selection([
        ('retraso', 'Por Retraso'),
        ('dano_leve', 'Por Daño Leve'),
        ('dano_grave', 'Por Daño Grave'),
        ('perdida', 'Por Pérdida'),
        ('retraso_y_dano', 'Por Retraso y Daño')
    ], string='Tipo de Multa', required=True, default='retraso')
    descripcion = fields.Text(string='Descripción')
    state = fields.Selection([
        ('pendiente', 'Pendiente'),
        ('pagada', 'Pagada'),
        ('cancelada', 'Cancelada')
    ], string='Estado', default='pendiente', required=True)

    def action_pagar(self):
        self.ensure_one()
        self.state = 'pagada'
        
        if self.prestamo_id.fecha_devolucion:
            self.prestamo_id.write({'estado': 'd'})
        
        _logger.info(f"Multa {self.name} marcada como pagada")