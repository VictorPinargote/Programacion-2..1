from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta

class BibliotecaUsuarios(models.Model):
    _name = 'biblioteca.usuarios'
    _description = 'biblioteca.usuarios'
    _rec_name = 'nombre_usuario'

    nombre_usuario = fields.Char(string='Nombre Completo', required=True)
    cedula_usuario = fields.Char(string='ID o Cédula', required=True, copy=False, index=True)
    telefono_usuario = fields.Char(string='Télefono', required=True)
    mail = fields.Char(string='Correo Eléctronico')
    activo = fields.Boolean(string='Activo', default=True)

    cedula_Ecu = {
        'Guayas': 9,
        'Pichincha': 17,
        'Azuay': 1,
        'Cañar': 2,
        'Chimborazo': 6,
    }

    @api.constrains('cedula_usuario')
    def _check_cedula_completa(self):
        for record in self:
            ci = record.cedula_usuario

            if not ci:
                continue

            if len(ci) != 10 or not ci.isdigit():
                raise ValidationError(" La cédula debe tener exactamente 10 dígitos numéricos.")

            provincia = int(ci[0:2])
            if not (1 <= provincia <= 24):
                raise ValidationError("El código de provincia es inválido (debe ser entre 01 y 24).")

            coeficientes = [2, 1, 2, 1, 2, 1, 2, 1, 2]
            suma_total = 0

            for i in range(9):
                digito = int(ci[i])
                valor_multiplicado = digito * coeficientes[i]
                valor_reducido = valor_multiplicado - 9 if valor_multiplicado >= 10 else valor_multiplicado
                suma_total += valor_reducido

            residuo = suma_total % 10
            digito_esperado = 10 - residuo if residuo != 0 else 0
            digito_real = int(ci[9])

            if digito_real != digito_esperado:
                raise ValidationError(
                    "El número de cédula es inválido. No cumple con la fórmula de verificación final."
                )

    @api.constrains('mail')
    def _check_valid_mail(self):
        for record in self:
            if record.mail and not email_re.match(record.mail):
                raise ValidationError("El formato del correo electrónico no es el correcto.")