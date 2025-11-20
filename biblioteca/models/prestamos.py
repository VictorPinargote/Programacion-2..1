from odoo import models, fields, api
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError, UserError
import logging

from odoo.models import TransientModel

_logger = logging.getLogger(__name__)

class BibliotecaWizard(models.TransientModel):
    _name= "biblioteca.wizard"
    _description =  "wizard para devolución de prestamos"

    prestamo_id = fields.Many2one('biblioteca.prestamo')
    evaluacion_libro = fields.Selection([
        ('b', 'Buen estado'),
        ('d', 'Deterioro/Daño'),
        ('p', 'Pérdida Total')
    ], string='Evaluar Estado al Devolver', default='b')

    observaciones= fields.Char(string='Observaciones')
    
    def cerrar_prestamo(self):
        self.prestamo_id.evaluacion_libro = self.evaluacion_libro
        self.prestamo_id.observaciones = self.observaciones
        self.prestamo_id.estado = 'd'


class BibliotecaPrestamos(models.Model):
    _name = 'biblioteca.prestamo'
    _description = 'biblioteca.prestamo'

    name = fields.Char(string='Código del Prestamo')
    usuario_id = fields.Many2one('biblioteca.usuarios')
    fecha_prestamo = fields.Datetime(default=datetime.now(), string='Fecha Prestamo')
    fecha_devolucion = fields.Datetime(string='Fecha Devolución')
    fecha_maxima = fields.Datetime(compute='_compute_fecha_devolucion_', string='Fecha máxima', store=True)
    libros_prestados_id= fields.Many2many('biblioteca.libro', string='Libros Prestados')
    multa_bol = fields.Boolean(string='Multado')
    multa = fields.Float()
    evaluacion_libro = fields.Selection([
        ('b', 'Buen estado'),
        ('d', 'Deterioro/Daño'),
        ('p', 'Pérdida Total')
    ], string='Evaluar Estado al Devolver', default='b')
    observaciones= fields.Char(string='Observaciones')
    # disponiblidad_libro=
    estado = fields.Selection([('b', 'Borrador'), ('p', 'Prestado'), ('m', 'Multa'), ('d', 'Devuelto')],
                              string='Estado', default='b')
    usuario = fields.Many2one('res.users', string='Autorizado por ', default=lambda self: self.env.uid)

    multa_ids = fields.One2many(
        'biblioteca.multa',
        'prestamo_id',
        string='Multas Generadas'
    )
    
    def devolver(self):
        
        suma = 1  + 2
        return {
            'name': 'Cerrar prestamo',
            'type': 'ir.actions.act_window',
            'res_model': 'biblioteca.wizard',
            'view_mode': 'form',
            'target': 'new',
            'view_id': self.env.ref('biblioteca.biblioteca_wizard_form').id,
            'context': {'default_prestamo_id': self.id, 'default_observaciones': suma}
        }

    @api.depends('fecha_maxima', 'fecha_prestamo')
    def _compute_fecha_devolucion_(self):
        for record in self:
            if record.fecha_prestamo:
                record.fecha_maxima = record.fecha_prestamo + timedelta(days=7)
            else:
                record.fecha_maxima = False

    @api.model
    def _check_prestamos_vencidos(self):
        try:
            template = self.env.ref('biblioteca.mail_template_book_loan_overdue')
        except ValueError:
            _logger.error("No se pudo encontrar la plantilla 'biblioteca.mail_template_book_loan_overdue'.")
            template = None

        busqueda_prestamos = [('estado', '=', 'p'),
                              ('fecha_maxima', '<', datetime.now())

                              ]

        prestamos_vencidos = self.env['biblioteca.prestamo'].search(busqueda_prestamos)

        _logger.info(f"Encontrados {len(prestamos_vencidos)} préstamos vencidos nuevos.")

        for prestamo in prestamos_vencidos:
            dias = (datetime.now() - prestamo.fecha_maxima).days
            multa_total_inicial = max(dias, 0) * 1.0

            if multa_total_inicial > 0:
                try:
                    multa_codigo = self.env['ir.sequence'].next_by_code('biblioteca.multa')
                except Exception:
                    multa_codigo = 'ERR-RET'

                usuario_cron_id = self.env.user.id
                usuario_multado_id = prestamo.usuario_id.id if prestamo.usuario_id else False

                self.env['biblioteca.multa'].create({
                    'prestamo_id': prestamo.id,
                    'es_retraso': True,
                    'costo_multa': multa_total_inicial,
                    'multa': f'Multa generada automáticamente por retraso de {dias} días',
                    'codigo_multa': multa_codigo,
                    'usuario_autorizador': usuario_cron_id,
                    'usuario_multado_id': usuario_multado_id,
                })

                prestamo.write({
                    'estado': 'm',
                    'multa_bol': True,
                    'multa': multa_total_inicial
                })

            if template and prestamo.usuario_id and prestamo.usuario_id.mail:
                _logger.info(
                    f"Enviando correo de vencimiento para préstamo {prestamo.name} a {prestamo.usuario_id.mail}")
                try:
                    template.send_mail(prestamo.id, force_send=True)
                except Exception as e:
                    _logger.error(f"Error al enviar correo para {prestamo.name}: {e}")

        prestamos_con_multa = self.env['biblioteca.prestamo'].search([
            ('estado', '=', 'm'),
            ('fecha_maxima', '!=', False),
            ('id', 'not in', prestamos_vencidos.ids)
        ])

        _logger.info(f"Actualizando {len(prestamos_con_multa)} multas existentes.")

        for prestamo in prestamos_con_multa:
            if isinstance(prestamo.fecha_maxima, datetime):
                dias = (datetime.now() - prestamo.fecha_maxima).days
                multa_total = max(dias, 0) * 1.0
                prestamo.write({'multa': multa_total})

    def write(self, vals):
        seq = self.env.ref('biblioteca.sequence_codigo_prestamos').next_by_code('biblioteca.prestamo')
        vals['name'] = seq
        return super(BibliotecaPrestamos, self).write(vals)

    def create (self, vals):
        if not vals.get('libros_prestados_id'):
            raise ValidationError("Seleecione un libro antes de prestar ")
        return super(BibliotecaPrestamos, self).create(vals)


    def generar_prestamo(self):
        for record in self:
            print("Generando Prestamo")
            if len(record.libros_prestados_id)== 0:
                raise ValidationError("Seleecione un libro antes de prestar ")
            if record.estado == 'b':
                record.write({'estado': 'p'})
        return True


    def action_devolver_y_evaluar(self):
        self.ensure_one()
        current_datetime = fields.Datetime.now()

        if self.estado in ('b', 'd'):
            raise UserError("El préstamo no está activo o ya fue devuelto.")

        fine_amount = 0.0
        fine_description = 'Multa por Daño/Pérdida: '
        es_perdida = False
        es_deterioro = False

        if self.evaluacion_libro == 'p':
            fine_amount = 50.0
            fine_description += 'PÉRDIDA Total (No devuelto).'
            es_perdida = True

        elif self.evaluacion_libro == 'd':
            fine_amount = 10.0
            fine_description += 'DETERIORO del libro.'
            es_deterioro = True

        if fine_amount > 0:

            try:
                multa_codigo = self.env['ir.sequence'].next_by_code('biblioteca.multa')
            except Exception:
                multa_codigo = 'COD-DAÑO-ERROR'

            usuario_autorizador_id = self.env.user.id
            usuario_multado_id = self.usuario_id.id if self.usuario_id else False

            self.env['biblioteca.multa'].create({
                'prestamo_id': self.id,
                'es_perdida': es_perdida,
                'es_deterioro': es_deterioro,
                'es_retraso': False,
                'costo_multa': fine_amount,
                'multa': fine_description,
                'codigo_multa': multa_codigo,
                'usuario_autorizador': usuario_autorizador_id,
                'usuario_multado_id': usuario_multado_id,
            })

        self.write({
            'estado': 'd',
            'fecha_devolucion': current_datetime,
        })

    def action_devolucion_normal(self):
        self.ensure_one()
        current_datetime = fields.Datetime.now()

        if self.fecha_maxima and self.fecha_maxima < current_datetime:
            dias_retraso = (current_datetime - self.fecha_maxima).days

            raise UserError(
                f"El préstamo está vencido por {dias_retraso} días. "
                "Debe usar el botón 'Devolver y Evaluar Estado' para que el sistema procese la multa por retraso."
            )

        self.write({
            'estado': 'd',
            'fecha_devolucion': current_datetime,
            'evaluacion_libro': 'b'
        })
        return True


