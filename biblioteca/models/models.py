from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import requests
import logging
import urllib.parse


_logger = logging.getLogger(__name__)

class Biblioteca(models.Model):
    _name = 'biblioteca.libro'
    _description = 'biblioteca.libro'
    _rec_name= 'nombre_libro'
    
    codigo_libro= fields.Char(string='Código del Libro')
    isbn= fields.Char(string='ISBN')
    nombre_libro = fields.Char(string='Nombre Libro')
    autor_id = fields.One2many('biblioteca.autor', 'libros', string='Autor Libro')
    categoria=fields.Char(string='Categoría')
    publicacion= fields.Char(string='Año de Publicaciòn')
    ejemplares= fields.Integer(string='Numero ejemplares')
    costo = fields.Char(string='Costo')
    description = fields.Text(string='Resumen libro')
    ubicacion= fields.Char(string='Ubicación fisica')

    autor_ids = fields.Many2many(
        'biblioteca.autor',       
        string='Autores'
    )

    def buscar_por_titulo(self):
        self.ensure_one()
        if not self.nombre_libro:
           raise UserError ("Por favor, ingrese un Título antes de buscar.")
    
        titulo_limpio = self.nombre_libro.strip()
        titulo_encoded = urllib.parse.quote_plus(titulo_limpio)
        
        url_busqueda = f"https://openlibrary.org/search.json?title={titulo_encoded}"
        _logger.info(f"Buscando en Open Library por título: {url_busqueda}")

        try:
            response_busqueda = requests.get(url_busqueda, timeout=10)
            response_busqueda.raise_for_status()
            data_busqueda = response_busqueda.json()

            if not data_busqueda or not data_busqueda.get('docs'):
                raise UserError(f"No se encontró ningún libro con el título '{self.nombre_libro}'.")

            vals_para_actualizar = {}
            primer_resultado_valido = None

            for resultado in data_busqueda.get('docs', []):
                
                if not resultado.get('author_name') and not resultado.get('publish_date'):
                    continue 

                primer_resultado_valido = resultado

                if resultado.get('publish_date'):
                    vals_para_actualizar['publicacion'] = resultado['publish_date'][0]
                
                if resultado.get('subject'):
                    nombres_categorias = [cat for cat in resultado.get('subject', [])[:4]]
                    if nombres_categorias:
                        vals_para_actualizar['categoria'] = ", ".join(nombres_categorias)

                if not self.isbn and resultado.get('isbn'):
                    vals_para_actualizar['isbn'] = resultado['isbn'][0]

                work_key = resultado.get('key')
                if work_key:
                    try:
                        url_detalle = f"https://openlibrary.org{work_key}.json"
                        response_detalle = requests.get(url_detalle, timeout=10)
                        response_detalle.raise_for_status()
                        data_detalle = response_detalle.json()
                        
                        description_info = data_detalle.get('description')
                        
                        if description_info:
                            if isinstance(description_info, str):
                                vals_para_actualizar['description'] = description_info
                            elif isinstance(description_info, dict) and description_info.get('value'):
                                vals_para_actualizar['description'] = description_info.get('value')
                        
                        break 
                    except requests.exceptions.RequestException as e:
                        _logger.warning(f"Error en segunda llamada API para la llave {work_key}: {e}")
                        continue

                break 

            if primer_resultado_valido and primer_resultado_valido.get('author_name'):
                lista_ids_autores = []
                Autor = self.env['biblioteca.autor']
                
                for nombre_completo in primer_resultado_valido.get('author_name', []):
                    autor_existente = Autor.search([('nombre_autor', '=', nombre_completo)], limit=1)
                    if autor_existente:
                        lista_ids_autores.append(autor_existente.id)
                    else:
                        nuevo_autor = Autor.create({'nombre_autor': nombre_completo})
                        lista_ids_autores.append(nuevo_autor.id)
                
                if lista_ids_autores:
                    vals_para_actualizar['autor_ids'] = [(6, 0, lista_ids_autores)]

            if vals_para_actualizar:
                _logger.info(f"Actualizando libro '{self.nombre_libro}' con datos: {vals_para_actualizar}")
                self.write(vals_para_actualizar)
            else:
                raise UserError(f"No se encontraron datos suficientes (autor, fecha) para autocompletar el libro '{self.nombre_libro}'.")

        except requests.exceptions.RequestException as e:
            _logger.error(f"Error al conectar con Open Library (búsqueda por título): {e}")
            raise UserError(f"Error de conexión: {e}")
        
        return True

    def buscar_isbn(self):
        self.ensure_one()
        if not self.isbn:
           raise UserError ("Por favor, ingrese un ISBN antes de buscar.")
    
        isbn_limpio = self.isbn.strip().replace('-', '')
        url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn_limpio}&format=json&jscmd=data"
    
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            book_key = f"ISBN:{isbn_limpio}"

            if not data or book_key not in data:
                raise UserError(f"No se encontró información para el ISBN '{self.isbn}'.")

            book_info = data[book_key]
            vals_para_actualizar = {}

            if book_info.get('title'):
                vals_para_actualizar['nombre_libro'] = book_info.get('title')
            if book_info.get('publish_date'):
                vals_para_actualizar['publicacion'] = book_info.get('publish_date')
            
            if book_info.get('notes'):
                vals_para_actualizar['description'] = book_info.get('notes')

            if book_info.get('subjects'):
                nombres_categorias = [cat.get('name') for cat in book_info.get('subjects', [])[:4]]
                nombres_categorias = [name for name in nombres_categorias if name]
                if nombres_categorias:
                    vals_para_actualizar['categoria'] = ", ".join(nombres_categorias)

            if book_info.get('authors'):
                lista_ids_autores = []
                Autor = self.env['biblioteca.autor']
                
                for autor_data in book_info['authors']:
                    nombre_completo = autor_data['name']

                    autor_existente = Autor.search([('nombre_autor', '=', nombre_completo)], limit=1)
                    
                    if autor_existente:
                        lista_ids_autores.append(autor_existente.id)
                    else:
                        nuevo_autor = Autor.create({'nombre_autor': nombre_completo})
                        lista_ids_autores.append(nuevo_autor.id)
                
                if lista_ids_autores:

                    vals_para_actualizar['autor_ids'] = [(6, 0, lista_ids_autores)]

            if vals_para_actualizar:
                self.write(vals_para_actualizar)

        except requests.exceptions.RequestException as e:
            _logger.error(f"Error al conectar con Open Library: {e}")
            raise UserError(f"Error de conexión: {e}")
        
        return True


class BibliotecaUbicacion(models.Model):
    _name='biblioteca.ubicacion'
    _description='biblioteca.ubicacion'
    _rec_name= 'ubicacion_libro'

    ubicacion_libro= fields.Char(string='Ubicación Del libro', required=True)
    codigo_ubicacion= fields.Char(string='Código/Abreviatura', required=True)
    descripcion= fields.Text(string='Notas de Ubicación' , required=True)
