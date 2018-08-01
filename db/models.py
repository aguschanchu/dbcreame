from django.db import models
from django.utils.safestring import mark_safe
from .tools import import_from_thingi
import uuid
import datetime

'''
Modelos internos (almacenados en la DB)
'''

class Autor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=300)
    username = models.CharField(max_length=300,unique=True)
    contact_email = models.EmailField(blank=True,null=True)

    def __str__(self):
        return self.name

'''
Clases accesorias
'''
class Categoria(models.Model):
    name = models.CharField(max_length=100,unique=True)

    def __str__(self):
        return self.name

class Tag(models.Model):
    name = models.CharField(max_length=300,unique=True)

    def __str__(self):
        return self.name

class Polinomio(models.Model):
    #Polinomio en forma p(x) = \sum^0_{n=0} a_n x^n
    a0 = models.FloatField(default=0)
    a1 = models.FloatField(default=0)
    a2 = models.FloatField(default=0)
    a3 = models.FloatField(default=0)
    a4 = models.FloatField(default=0)
    a5 = models.FloatField(default=0)

    def __str__(self):
        return "{} x^5+ {} x^4+ {} x^3+ {} x^2+ {} x+ {}".format(self.a0,self.a1,self.a2,self.a3,self.a4,self.a5)

class Imagen(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    photo = models.ImageField(upload_to='images/')

    def __str__(self):
        return self.photo.name

    def name(self):
        return self.photo.name

    def view_image(self):
        return mark_safe('<img src="{}" width="400" height="300" />'.format(self.photo.url))

'''class Album(models.Model):
    #Coleccion de fotos de un objeto
    pic0 = models.ImageField(upload_to='images/')
    pic1 = models.ImageField(blank=True,null=True,upload_to='images/')
    pic2 = models.ImageField(blank=True,null=True,upload_to='images/')
    pic3 = models.ImageField(blank=True,null=True,upload_to='images/')
    pic4 = models.ImageField(blank=True,null=True,upload_to='images/')
    pic5 = models.ImageField(blank=True,null=True,upload_to='images/')

    def imagen_principal(self):
        return mark_safe('<img src="{}" width="400" height="300" />'.format(self.pic0.url))

    def __str__(self):
        return self.pic0.name'''

class ArchivoSTL(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to='stl/')

    #Tiempo de impresion en escala 1, en segundos
    printing_time_default = models.IntegerField(default=0)
    time_as_a_function_of_scale = models.ForeignKey(Polinomio,on_delete=models.SET_NULL,null=True)
    #Dimensiones del objeto en escala 1, en mm
    size_x_default = models.FloatField(default=10)
    size_y_default = models.FloatField(default=10)
    size_z_default = models.FloatField(default=10)
    #Peso del objeto en escala 1, en g
    weight_default = models.FloatField(default=10)

    def __str__(self):
        return self.file.name

    def name(self):
        return self.file.name

'''
Clase de referencia externa. La idea es asignar id_externa al identificador que se utiliza en el repositorio indicado
'''

repositorios = (
('thingiverse', 'Thingiverse'),
('youmagine', 'YouMagine'),
('externo', 'Extero (archivo propio)'),
)

class ReferenciaExterna(models.Model):
    external_id = models.CharField(max_length=100)
    repository = models.CharField(choices=repositorios,max_length=300)

    def __str__(self):
        return self.repository+':'+self.external_id


class Objeto(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=300)
    description = models.TextField(blank=True,null=True)
    like_count = models.IntegerField(blank=True,default=0)
    main_image = models.ImageField(upload_to='images/')
    images = models.ManyToManyField(Imagen)
    files = models.ManyToManyField(ArchivoSTL)
    author = models.ForeignKey(Autor,on_delete=models.PROTECT)
    creation_date = models.DateTimeField(default=datetime.datetime.now)
    category = models.ManyToManyField(Categoria)
    #No estoy 100% seguro de que esta sea la mejor implementacion para los tags. En particular, por la busqueda
    tags = models.ManyToManyField(Tag)
    external_id = models.ForeignKey(ReferenciaExterna,on_delete=models.SET_NULL,null=True)
    #Se muestra en el catalogo?
    hidden = models.BooleanField(default=False)

    def view_main_image(self):
        return mark_safe('<img src="{}" width="400" height="300" />'.format(self.main_image.url))

class Usuario(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.EmailField()
    password = models.CharField(max_length=300)
    liked_objects = models.ManyToManyField(Objeto)
    address = models.CharField(max_length=300)

    def __str__(self):
        return self.username

class ObjetoPersonalizado(models.Model):
    objeto = models.ForeignKey(Objeto,on_delete=models.PROTECT)
    color = models.CharField(max_length=100,default='white')
    #A partir de la escala y el objeto, podemos calcular las dimensiones
    scale = models.FloatField(default=1)
    weight_default = models.FloatField(default=10)

class Compra(models.Model):
    estados = (
    ('accepted', 'Aceptado'),
    ('printing', 'Imprimiendo'),
    ('shipped', 'Enviado'),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    purchased_objects = models.ManyToManyField(ObjetoPersonalizado)
    date = models.DateTimeField(default=datetime.datetime.now)
    status = models.CharField(choices=repositorios,max_length=300)
    delivery_address = models.CharField(max_length=300)
    #Este campo hay que optimizarlo segun el output de MP
    payment_method = models.CharField(max_length=300)

'''
Modelos externos (utilizados para serializar información)
'''

class ObjetoThingi(models.Model):
    id_externa = models.IntegerField()
    #Lista de archivos thing a tener en cuenta. Puede ser 'all', o una lista en formato json
    file_list = models.CharField(max_length=300)
