from django.db import models
import datetime

# Create your models here.

class Objeto(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=300)
    description = models.TextField(blank=True,null=True)
    like_count = models.IntegerField(blank=True,default=0)
    #jpeg=
    #files=
    author = models.ForeignKey(Autor,on_delete=models.PROTECT)
    creation_date = models.DateTimeField(default=datetime.datetime.now)
    category = models.ManyToManyField(Categoria)
    #No estoy 100% seguro de que esta sea la mejor implementacion para los tags. En particular, por la busqueda
    tags = models.ManyToManyField(Tag)
    external_id = models.ForeignKey(ReferenciaExterna,on_delete=models.SET_NULL,null=True)
    printing_time_default = models.IntegerField(default=0)

class Autor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=300)
    username = models.CharField(max_length=300)
    contact_email = models.EmailField(blank=True,null=True)

'''
Clase de referencia externa. La idea es asignar id_externa al identificador que se utiliza en el repositorio indicado
'''

repositorios = (
('thingiverse', 'Thingiverse'),
('youmagine', 'YouMagine'),
('externo', 'Extero (archivo propio)'),
)

class ReferenciaExterna(models.Model):
    external_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    repository = models.CharField(choices=repositorios)


'''
Clases accesorias
'''
class Categoria(models.Model):
    name = models.CharField(max_length=100)

class Tag(models.Model):
    name = models.CharField(max_length=300)
