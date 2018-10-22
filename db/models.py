from django.db import models
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.core.files import File
from django.core.files.base import ContentFile
from thingiverse.tasks import translate_category, translate_tag
from .tools import stl_to_sfb
from .tools import dbdispatcher
from .render.blender import render_image
from .render.plot_poly import polyplot
import uuid
import datetime
import os
import shutil
import trimesh
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from google.cloud import translate
from django_mercadopago import models as MPModels
from django.core.validators import MinLengthValidator
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFit


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
    name_es = models.CharField(max_length=100,blank=True,null=True)

    def __str__(self):
        return self.name

    def translate_es(self,translate_client=None,force=False):
        if self.name_es == None or force:
            if translate_client == None:
                translate_client = translate.Client()
            translation = translate_client.translate(self.name,source_language='en',target_language='es')
            self.name_es = translation['translatedText']
            self.save()

@receiver(post_save, sender=Categoria)
def translate_category_signal(sender, instance, created, **kwargs):
    if created:
        translate_category.delay(instance.id)


class Tag(models.Model):
    name = models.CharField(max_length=300,unique=True)
    name_es = models.CharField(max_length=300,blank=True,null=True)

    def __str__(self):
        return self.name

    def translate_es(self,translate_client=None,force=False):
        if self.name_es == None or force:
            if translate_client == None:
                translate_client = translate.Client()
            translation = translate_client.translate(self.name,source_language='en',target_language='es')
            self.name_es = translation['translatedText']
            self.save()

@receiver(post_save, sender=Tag)
def translate_tag_signal(sender, instance, created, **kwargs):
    if created:
        translate_tag.delay(instance.id)

class Polinomio(models.Model):
    #Polinomio en forma p(x) = \sum^0_{n=0} a_n x^n
    a0 = models.FloatField(default=0)
    a1 = models.FloatField(default=0)
    a2 = models.FloatField(default=0)
    a3 = models.FloatField(default=0)
    a4 = models.FloatField(default=0)
    a5 = models.FloatField(default=0)
    plot = models.ImageField(upload_to='images/plots',null=True,blank=True)

    def __str__(self):
        return "{} x^5+ {} x^4+ {} x^3+ {} x^2+ {} x+ {}".format(self.a5,self.a4,self.a3,self.a2,self.a1,self.a0)

    def coefficients_list(self):
        return [self.a5,self.a4,self.a3,self.a2,self.a1,self.a0]

@receiver(post_save, sender=Polinomio)
def plot_poly(sender, instance, update_fields, **kwargs):
    if update_fields == None:
        polyplot(instance)

class Color(models.Model):
    name = models.CharField(max_length=100)
    #Hex color code
    code = models.CharField(max_length=6, validators=[MinLengthValidator(6)])
    #Esta el color en stock?
    available = models.BooleanField(blank=True,default=True)
    #Referencia de color para los modelos de AR (es un cubo en sfb)
    sfb_color_reference = models.FileField(upload_to='sfb/',null=True,blank=True)

    def __str__(self):
        return self.name

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

origenes = (
    ('human', 'Agregado por un humano'),
    ('vision', 'Resultado de busqueda en visionapi'),
)

class Objeto(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=300)
    name_es = models.CharField(max_length=300,null=True,blank=True)
    description = models.TextField(blank=True,null=True)
    like_count = models.IntegerField(blank=True,default=0)
    main_image = models.ImageField(upload_to='images/',null=True)
    main_image_thumbnail = ImageSpecField(source='main_image', processors=[ResizeToFit(width=800, height=600, upscale=False)], format='JPEG', options={'quality': 40})
    author = models.ForeignKey(Autor,on_delete=models.PROTECT)
    creation_date = models.DateTimeField(default=timezone.now)
    category = models.ManyToManyField(Categoria)
    tags = models.ManyToManyField(Tag)
    external_id = models.OneToOneField(ReferenciaExterna,on_delete=models.SET_NULL,null=True)
    #Se muestra en el catalogo?
    hidden = models.BooleanField(default=False)
    #Tiene algun descuento particular? precio_descontado = precio * discount
    discount = models.FloatField(blank=True,default=1)
    #Colores del objeto
    default_color = models.ForeignKey(Color,on_delete=models.SET_NULL,null=True,blank=True,related_name='default_color')
    popular_color = models.ForeignKey(Color,on_delete=models.SET_NULL,null=True,blank=True,related_name='popular_color')
    #Origen del objeto (AKA como fue agregado)
    origin = models.CharField(choices=origenes,max_length=30,null=True)
    #Fueron descargados los STL? (y objetos relacionados con este)
    partial = models.BooleanField(default=False)

    def suggested_color(self):
        if self.default_color != None:
            return self.default_color
        elif self.popular_color != None:
            return self.popular_color
        else:
            return Color.objects.first()

    def update_popular_color(self):
        colors_ordered = [a.color.id for a in ObjetoPersonalizado.objects.filter(object_id=self)]
        self.popular_color = Color.objects.get(pk=max(colors_ordered,key=colors_ordered.count))
        self.save()

    def view_main_image(self):
        return mark_safe('<img src="{}" width="400" height="300" />'.format(self.main_image.url))

    def translate_es(self,translate_client=None,force=False):
        if self.name_es == None or force:
            if translate_client == None:
                translate_client = translate.Client()
            translation = translate_client.translate(self.name,source_language='en',target_language='es')
            self.name_es = translation['translatedText']
            self.save(update_fields=['name_es'])

    #En lugar de sumar default_printing_time, evaluamos tiempo(escala) en 1. Esto, es para evitar difierencias al usar el polinomio
    def printing_time_default_total(self):
        return round(sum([sum(a.time_as_a_function_of_scale.coefficients_list()) for a in self.files.all()]))

    @staticmethod
    def search_objects(query):
        objetos_n = Objeto.objects.none()
        objetos_t = Objeto.objects.none()
        for word in query:
            objetos_n = objetos_n | Objeto.objects.filter(name__contains=word) | Objeto.objects.filter(name_es__contains=word)
        for word in query:
            objetos_t = objetos_t | Objeto.objects.filter(tags__name_es=word) | Objeto.objects.filter(tags__name=word)

        return (objetos_t | objetos_n).distinct()

'''
Modelos accesorios
'''
class ArchivoSTL(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to='stl/')
    object = models.ForeignKey(Objeto,blank=True,null=True,on_delete=models.CASCADE,related_name='files')
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

class Imagen(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    photo = models.ImageField(upload_to='images/')
    object = models.ForeignKey(Objeto,blank=True,null=True,on_delete=models.CASCADE,related_name='images')

    def __str__(self):
        return self.photo.name

    def name(self):
        return self.photo.name

    def view_image(self):
        return mark_safe('<img src="{}" width="400" height="300" />'.format(self.photo.url))

#Contiene los archivos necesarios para la visualizacion AR de cada Objeto
class ModeloAR(models.Model):
    combined_stl = models.FileField(upload_to='stl/',blank=True,null=True)
    #El combinado fue revisado por un humano?
    human_flag = models.BooleanField(blank=True,default=False)
    sfb_file = models.FileField(upload_to='sfb/',blank=True,null=True)
    sfb_file_rotated = models.FileField(upload_to='sfb/',blank=True,null=True)
    #Indica si muchos usuarios solicitaron rotar el objeto
    rotated = models.BooleanField(blank=True,default=False)
    object = models.OneToOneField(Objeto, on_delete=models.CASCADE,null=True)
    combined_size_x = models.FloatField(blank=True,default=0)
    combined_size_y = models.FloatField(blank=True,default=0)
    combined_size_z = models.FloatField(blank=True,default=0)

    def image_render(self):
        return self.modeloarrender.image_render

    def combined_dimensions(self):
        return [self.combined_size_x, self.combined_size_y, self.combined_size_z]

    def calculate_rotated(self):
        tracked_rotations = [a.rotated for a in SfbRotationTracker.objects.filter(object=self.object)]
        #A partir de 4 podemos usar LGN
        if len(tracked_rotations) > 0:
            self.rotated = True if tracked_rotations.count(True)/len(tracked_rotations) > 0.5 else False
        self.save(update_fields=['rotated'])

    #Si el modelo tiene un unico objeto, el STL combinado, es el mismo
    def check_for_single_object_file(self):
        if len(self.object.files.all()) == 1:
            self.combined_stl = self.object.files.all()[0].file
            self.human_flag = True
            self.save(update_fields=['combined_stl','human_flag'])
            self.calculate_combined_dimensions()
            return True
        else:
            return False

    def arrange_and_combine_files(self):
        res = stl_to_sfb.combine_stls_files(self.object)
        with open(res+'/plate00.stl','rb') as f:
            self.combined_stl.save(self.object.name+'.stl',File(f),save=False)
            self.save(update_fields=['combined_stl'])
        shutil.rmtree(res)

    def combine_stl(self):
        new_file = stl_to_sfb.combine_stl_with_correct_coordinates(self)
        #Borramos el archivo anterior
        #self.combined_stl.delete()
        self.combined_stl.save(name,new_file,save=False)
        #Ejecutamos la funcion de guardar a parte, para que evitar un loop infinito con los signals
        self.save(update_fields=['combined_stl','human_flag'])
        #Actualizamos el tamaño del objeto
        self.calculate_combined_dimensions()

    def create_sfb(self,generate=False):
        if not self.combined_stl.name:
            #No tenemos STL combinado. Intentamos generarlo?
            if generate:
                if not self.check_for_single_object_file():
                    self.arrange_and_combine_files()
            else:
                return False
        #Creamos ambos SFB
        for field, fieldname, rotate in [(self.sfb_file,'sfb_file',False),(self.sfb_file_rotated,'sfb_file_rotated',True)]:
            sfb_path = stl_to_sfb.convert(settings.BASE_DIR+self.combined_stl.url,self.combined_stl.name,rotate)
            with open(sfb_path,'rb') as f:
                field.save(sfb_path.split('/')[-1],File(f),save=False)
                self.save(update_fields=[fieldname])
                os.remove(sfb_path)

    def calculate_combined_dimensions(self):
        #Calcula la bounding_box sin orientar. Se puede cambiar por  .bounding_box_oriented.primitive.transform
        if self.human_flag:
            self.combined_size_x, self.combined_size_y, self.combined_size_z = list(trimesh.load(settings.BASE_DIR+self.combined_stl.url).bounding_box.extents)
            self.save(update_fields=['combined_size_x','combined_size_y','combined_size_z'])

#Utilizados para actualizar las dimensiones del objeto al cambiar el stl_combinado
@receiver(post_save, sender=ModeloAR)
def update_combined_dimensions(sender, instance, update_fields, **kwargs):
    if update_fields == None:
        return False
    if instance.human_flag and 'combined_stl' in update_fields:
        instance.calculate_combined_dimensions()

class ModeloARRender(models.Model):
    image_render = models.FileField(upload_to='renders/',blank=True,null=True)
    model_ar = models.OneToOneField(ModeloAR, on_delete=models.CASCADE)

    def create_render(self):
        if not self.model_ar.combined_stl.name:
            return False
        png_path = render_image(self.model_ar)
        with open(png_path,'rb') as f:
            self.image_render.save(self.model_ar.combined_stl.name.split('.')[0],File(f))
        os.remove(png_path)

#Utilizados para actualizar el render al cambiar el ModeloAR
@receiver(post_save, sender=ModeloAR)
def create_modeloar_render(sender, instance, created, **kwargs):
    if created:
        ModeloARRender.objects.create(model_ar=instance)

@receiver(post_save, sender=ModeloAR)
def update_render_and_model(sender, instance, update_fields, **kwargs):
    #Lo reviso un humano? Lo actualizamos al STL combinado de ser asi
    if instance.human_flag and update_fields == None:
        instance.combine_stl()
        instance.create_sfb()
    if update_fields != None:
        #No queremos actualizar el objeto si solo fue flaggeado como rotado
        if 'rotated' in update_fields:
            return False
    instance.modeloarrender.create_render()
    instance.modeloarrender.save()


'''
Modelos de usuarios/compras
'''

class Usuario(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telephone = models.CharField(max_length=100,blank=True,null=True,default="")
    liked_objects = models.ManyToManyField(Objeto)

#Utilizados para actualizar el Usuario al cambiar el User de Django
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Usuario.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.usuario.save()

class DireccionDeEnvio(models.Model):
    usuario = models.ForeignKey(Usuario,on_delete=models.CASCADE,related_name='address_book')
    last_time_used = models.DateTimeField(default=timezone.now,blank=True)
    address = models.CharField(max_length=300,primary_key=True)
    notes = models.CharField(max_length=300,blank=True,default=None,null=True)

    class Meta:
        ordering = ['last_time_used']

class Compra(models.Model):
    estados = (
        ('pending-payment', 'Pago pendiente'),
        ('checkout-pending', 'Proceso de checkout no iniciado')
        ('accepted', 'Aceptado'),
        ('printing', 'Imprimiendo'),
        ('shipped', 'Enviado'),
        ('completed', 'Completado'),
        ('canceled', 'Cancelado'),
        ('error' , 'Error')
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False,blank=True)
    buyer = models.ForeignKey(Usuario,on_delete=models.CASCADE,blank=True,null=True)
    date = models.DateTimeField(default=timezone.now,blank=True)
    status = models.CharField(choices=estados,max_length=300,blank=True,default='checkout-pending')
    delivery_address = models.ForeignKey(DireccionDeEnvio,null=True,on_delete=models.SET_NULL,blank=True)
    payment_preferences = models.OneToOneField(MPModels.Preference,on_delete=models.CASCADE,blank=True,null=True)

    def thumbnail(self):
        return self.purchased_objects.first().object_id.main_image_thumbnail

@receiver(post_save, sender=MPModels.Payment)
def process_payment(sender, instance, created, **kwargs):
    if instance.status == "approved":
        compra = MPModels.Preference.objects.get(pk=instance.preference_id).compra
        dbdispatcher.new_payment(compra)

class ObjetoPersonalizado(models.Model):
    object_id = models.ForeignKey(Objeto,on_delete=models.PROTECT)
    color = models.ForeignKey(Color,on_delete=models.PROTECT)
    scale = models.FloatField(blank=True,default=1)
    quantity = models.IntegerField(blank=True,default=1)
    purchase = models.ForeignKey(Compra,on_delete=models.CASCADE,related_name='purchased_objects')

    def name(self):
        return self.object_id.name

#Utilizados para actualizar el color pricipal cuando se genera una orden nueva
@receiver(post_save, sender=ObjetoPersonalizado)
def update_suggested_color(sender, instance, created, **kwargs):
    if created:
        instance.object_id.update_popular_color()

'''
Modelos de trackeo
'''

#Trackear si los usuarios rotaron el objeto, o no
class SfbRotationTracker(models.Model):
    object = models.ForeignKey(Objeto, on_delete=models.CASCADE)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE,blank=True)
    rotated = models.BooleanField()

@receiver(post_save, sender=SfbRotationTracker)
def update_rotated_sfb(sender, instance, created, **kwargs):
    if created:
        instance.object.modeloar.calculate_rotated()
