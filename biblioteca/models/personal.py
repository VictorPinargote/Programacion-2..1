from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
from odoo.tools.mail import email_re

class BibliotecaPersonal(models.Model):
    _name = 'biblioteca.personal'
    _description = 'biblioteca.personal'
    _rec_name = 'nombre_personal'

    nombre_personal = fields.Char(string='Nombre', required=True)
    Apellido_personal = fields.Char(string='Apellido', required=True)
    cedula_personal = fields.Char(string='CI o Cédula', required=True)
    personal_telefono = fields.Char(string='Celular', required=True)
    personal_direccion = fields.Char(string='Dirección', required=True)
    personal_mail = fields.Char(string='Correo electrónico', required=True)

    # personal_encargada_prestamo_id= fields.One2many('biblioteca.prestamo','personal_prestar_libro_id', string='Persona autorizada')

    @api.depends('nombre_personal', "Apellido_personal")
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.nombre_personal}  {record.Apellido_personal}"

    cedula_Ecu = {
        'Guayas': 9,
        'Pichincha': 17,
        'Azuay': 1,
        'Cañar': 2,
        'Chimborazo': 6,
    }

    @api.constrains('cedula_personal')
    def _check_cedula(self):
        for record in self:
            ci = record.cedula_personal

            if ci and (len(ci) != 10 or not ci.isdigit()):
                raise ValidationError("La cédula debe tener exactamente 10 dígitos.")

            provincia = int(ci[0:2])
            if provincia < 1 or provincia > 24:
                raise models.ValidationError(" El código de provincia es inválido.")

            coeficientes = [2, 1, 2, 1, 2, 1, 2, 1, 2]
            suma_total = 0

            for indice in range(9):
                digito = int(ci[indice])
                coeficiente = coeficientes[indice]

                valor_multiplicado = digito * coeficiente

                if valor_multiplicado >= 10:
                    valor_reducido = valor_multiplicado - 9
                else:
                    valor_reducido = valor_multiplicado

                suma_total += valor_reducido

            residuo = suma_total % 10

            if residuo == 0:
                digito_verificador_esperado = 0
            else:
                digito_verificador_esperado = 10 - residuo

            digito_verificador_real = int(ci[9])

            if digito_verificador_real != digito_verificador_esperado:
                raise ValidationError(
                    "El número de cédula es inválido. No cumple con la fórmula de verificación del dígito final."
                )

    @api.constrains('personal_mail')
    def _check_valid_mail(self):
        for record in self:
            if record.personal_mail and not email_re.match(record.mail):
                raise ValidationError("El formato del correo electrónico no es el correcto.")