from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError

class Partner(models.Model):
    _inherit = 'res.partner'

    nacionalidad = fields.Char(string='Nacionalidad')
    fecha_nacimiento = fields.Datetime(string='Fecha de nacimiento')
    nacimiento= fields.Char(string='Nacimiento')
    sexo= fields.Selection([('m','masculino'), ('f','feminino')], string='Sexo')
