from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta



class BibliotecaMulta(models.Model):
    _name = 'biblioteca.multa'
    _description = 'biblioteca.multa'

    codigo_multa= fields.Char(string='Còdigo de multa')
    multa= fields.Char(string='Descripción de la Multa')
    costo_multa=fields.Float(string='Costo de la Multa')
    prestamo_id = fields.Many2one('biblioteca.prestamo', string='Préstamo Relacionado')

    es_perdida = fields.Boolean(string='Pérdida')
    es_deterioro = fields.Boolean(string='Deterioro')
    es_retraso = fields.Boolean(string='Retraso')

    usuario_autorizador = fields.Many2one(
        'res.users',
        string='Multa Generada Por',
        readonly=True
    )

    usuario_multado_id = fields.Many2one(
        'biblioteca.usuarios',
        string='Usuario Multado',

    )

    @api.constrains('es_perdida', 'es_deterioro', 'es_retraso')
    def _check_estado_libro(self):
        for record in self:
            if record.es_perdida and (record.es_deterioro or record.es_retraso):
                raise ValidationError(
                    'No se puede seleccionar "Pérdida" junto con "Deterioro" o "Retraso".'
                )