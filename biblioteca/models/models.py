from odoo import models, fields, api

class bibliotecaLibro(models.Model):
     _name = 'biblioteca.libro'
     _description = 'biblioteca.biblioteca'
     _rec_name = 'firstname'
     
     firstname = fields.Char(string="Nombre libro")
     author_id = fields.Many2one('biblioteca.autor', string="Autor Libro")
     value = fields.Integer(string="numero Ejemplares")
     value2 = fields.Float(compute="_value_pc", store=True, string="Costo")
     description = fields.Text(string ="Resumen Libro")

     @api.depends('value')
     def _value_pc(self):
         for record in self:
             record.value2 = float(record.value) / 100
             
class bibliotecaAutor(models.Model):
     _name = 'biblioteca.autor'
     _description = 'biblioteca.autor'
     
    firstname = fields.Char()
    lastname = fields.Char()
    
    @api.depends('firstname','lastname')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.firstname} {record.lastname}"