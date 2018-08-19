from django.db import models
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.core.files import File
from django.core.files.base import ContentFile
from .tools import import_from_thingi
from .tools import stl_to_sfb
import uuid
import datetime
import os
import shutil
import trimesh
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

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
        return "{} x^5+ {} x^4+ {} x^3+ {} x^2+ {} x+ {}".format(self.a5,self.a4,self.a3,self.a2,self.a1,self.a0)

class Imagen(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    photo = models.ImageField(upload_to='images/')

    def __str__(self):
        return self.photo.name

    def name(self):
        return self.photo.name

    def view_image(self):
        return mark_safe('<img src="{}" width="400" height="300" />'.format(self.photo.url))

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

#Contiene losfrom django.dispatch import receiver archivos necesarios para la visualizacion AR de cada Objeto
class ModeloAR(models.Model):
    combined_stl = models.FileField(upload_to='stl/',blank=True,null=True)
    #El combinado fue revisado por un humano?
    human_flag = models.BooleanField(blank=True,default=False)
    sfb_file = models.FileField(upload_to='sfb/',blank=True,null=True)

    def image_render(self):
        return self.modeloarrender.image_render

    #Si el modelo tiene un unico objeto, el STL combinado, es el mismo
    def check_for_single_object_file(self):
        if len(self.objeto.files.all()) == 1:
            self.combined_stl = self.objeto.files.all()[0].file
            self.human_flag = True
            self.save()
            return True
        else:
            return False

    def arrange_and_combine_files(self):
        res = stl_to_sfb.combine_stls_files(self.objeto)
        self.combined_stl.save(self.objeto.name+'.stl',File(open(res+'/plate00.stl','rb')))
        shutil.rmtree(res)

    def create_sfb(self,generate=False):
        if not self.combined_stl.name:
            #No tenemos STL combinado. Intentamos generarlo?
            if generate:
                if not self.check_for_single_object_file():
                    self.arrange_and_combine_files()
            else:
                return False
        sfb_path = stl_to_sfb.convert(self.combined_stl)
        self.sfb_file.save(sfb_path.split('/')[-1],File(open(sfb_path,'rb')))
        os.remove(sfb_path)

class ModeloARRender(models.Model):
    image_render = models.FileField(upload_to='renders/',blank=True,null=True)
    model_ar = models.OneToOneField(ModeloAR, on_delete=models.CASCADE)

    def create_render(self):
        if not self.model_ar.combined_stl.name:
            return False
        mesh = trimesh.load_mesh(settings.BASE_DIR+self.model_ar.combined_stl.url)
        self.image_render.save(self.model_ar.combined_stl.name.split('.')[0],ContentFile(mesh.scene().save_image()))

#Utilizados para actualizar el render al cambiar el ModeloAR
@receiver(post_save, sender=ModeloAR)
def create_modeloar_render(sender, instance, created, **kwargs):
    if created:
        ModeloARRender.objects.create(model_ar=instance)

@receiver(post_save, sender=ModeloAR)
def save_modeloar_render(sender, instance, **kwargs):
    instance.modeloarrender.create_render()
    instance.modeloarrender.save()



'''
Clase de referencia externa. La idea es asignar id_externa al identificador que se utiliza en el repositorio indicado
'''

repositorios = (
    ('thingiverse', 'Thingiverse'),
    ('youmagine', 'YouMagine'),
    ('externo', 'Externo (archivo propio)'),
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
    creation_date = models.DateTimeField(default=timezone.now)
    category = models.ManyToManyField(Categoria)
    ar_model = models.OneToOneField(ModeloAR, on_delete=models.CASCADE,null=True)
    tags = models.ManyToManyField(Tag)
    external_id = models.OneToOneField(ReferenciaExterna,on_delete=models.SET_NULL,null=True)
    #Se muestra en el catalogo?
    hidden = models.BooleanField(default=False)

    def view_main_image(self):
        return mark_safe('<img src="{}" width="400" height="300" />'.format(self.main_image.url))

'''
Modelos de usuarios/compras
'''

class Usuario(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    liked_objects = models.ManyToManyField(Objeto)
    address = models.CharField(max_length=300)

#Utilizados para actualizar el Usuario al cambiar el User de Django
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Usuario.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.usuario.save()

class ObjetoPersonalizado(models.Model):
    object_id = models.ForeignKey(Objeto,on_delete=models.PROTECT)
    color = models.CharField(max_length=100,default='white')
    scale = models.FloatField(blank=True,default=1)
    quantity = models.IntegerField(blank=True,default=1)

    def name(self):
        return self.object_id.name

class Compra(models.Model):
    estados = (
        ('accepted', 'Aceptado'),
        ('printing', 'Imprimiendo'),
        ('shipped', 'Enviado'),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    buyer = models.ForeignKey(Usuario,on_delete=models.CASCADE)
    purchased_objects = models.ManyToManyField(ObjetoPersonalizado)
    date = models.DateTimeField(default=datetime.datetime.now)
    status = models.CharField(choices=estados,max_length=300)
    delivery_address = models.CharField(max_length=300)
    #Este campo hay que optimizarlo segun el output de MP
    payment_method = models.CharField(max_length=300)

'''
Modelos externos (utilizados para serializar información)
'''

class ObjetoThingi(models.Model):
    estados = (
        ('processing', 'Procesando'),
        ('error', 'Error'),
        ('finished', 'Finalizado'),
    )
    external_id = models.IntegerField()
    #Lista de archivos thing a tener en cuenta. Puede ser 'all', o una lista en formato json
    file_list = models.CharField(max_length=300,blank=True,null=True)
    status = models.CharField(choices=estados,max_length=300,blank=True,default="processing")
