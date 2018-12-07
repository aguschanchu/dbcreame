from django.db import models
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField
from celery.result import AsyncResult
from db import models as modelos
import datetime
import trimesh
import json
import traceback

'''
Tenemos un limite de 300/5', queremos monitorear cada key, para no pasarnos
'''

class ApiKey(models.Model):
    quota = 290
    quota_interval = 5*60
    key = models.CharField(max_length=100)

    def clean(self):
        #¿Es valida?
        r = requests.get(settings.THINGIVERSE_API_ENDPOINT+'things/763622?access_token='+str(self.key)).json()
        if 'Unauthorized' in r.values():
            raise ValidationError('API key invalida')

    def make_query(self):
        event = QueryEvent.objects.create(key=self)

    def available(self, count=1):
        #Actualizamos la tabla de meters:
        for event in self.meter.all():
            if (datetime.datetime.now(datetime.timezone.utc)-event.date).seconds > self.quota_interval:
                event.delete()
        if len(self.meter.all()) + count <= self.quota:
            return True
        else:
            return False

    @staticmethod
    def get_api_key(count=1):
        for key in ApiKey.objects.all():
            if key.available(count):
                for _ in range(0,count):
                    key.make_query()
                return key.key
        else:
            return None

class QueryEvent(models.Model):
    date = models.DateTimeField(auto_now_add=True)
    key = models.ForeignKey(ApiKey, on_delete=models.CASCADE, related_name='meter')

class ObjetoThingiManager(models.Manager):

    def create_object(self, external_id, file_list=None, partial=False, origin=None, update_object=False, subtask_ids_list = None):
        from . import tasks
        object = self.create(external_id=external_id, file_list=file_list, partial=partial)
        # Ejecutamos la tarea
        job = tasks.add_object_from_thingiverse_chain(thingiid=external_id, file_list=file_list, partial=partial, origin=origin).apply_async(max_retries=300)
        object.celery_id = job.id
        object.save(update_fields=["celery_id"])
        return object

    def update_object(self, object_id, file_list=None, update_object=True, partial=False, subtask_ids_list = None):
        from . import tasks
        object = self.create(object_id=object_id,external_id=object_id.external_id.external_id, file_list=file_list, partial=partial, update_object=update_object)
        job = tasks.add_files_to_thingiverse_object.delay([object_id.id], file_list)
        object.celery_id = job.id
        object.save(update_fields=['celery_id','external_id'])
        return object

class ObjetoThingi(models.Model):
    estados = (
        ('QUEUED', 'En cola'),
        ('STARTED', 'Procesando'),
        ('FAILURE', 'Error'),
        ('SUCCESS', 'Finalizado'),
        ('RETRY', 'Esperando a ser reintentado'),
        ('NOT FOUND', 'Objeto no hallado'),
    )
    external_id = models.IntegerField(default=0)
    #Lista de archivos thing a tener en cuenta. Puede ser nulo (y por lo tanto, descarga todos) o una lista
    file_list = ArrayField(models.IntegerField(),null=True)
    status = models.CharField(choices=estados,max_length=300,blank=True,default="processing")
    celery_id = models.CharField(max_length=100,blank=True)
    object_id = models.ForeignKey('db.Objeto',null=True,on_delete=models.SET_NULL)
    partial = models.BooleanField(default=True)
    origin = models.CharField(max_length=200,blank=True,null=True)
    update_object = models.BooleanField(default=False)

    objects = ObjetoThingiManager()

    def update_status(self):
        res = AsyncResult(self.celery_id)
        self.status = res.state
        if res.ready():
            result = res.result
            try:
                self.object_id = modelos.Objeto.objects.get(pk=result[0])
                # Tiene imagen principal?
                if not self.object_id.main_image:
                    self.status = 'STARTED'
            except:
                print("Error al levantar objeto. Ver logs de Celery")
                self.object_id = None
                self.status = 'FAILURE'
            else:
                self.status = 'SUCCESS'
        self.save()

    def update_subtask_status(self):
        for t in self.subtasks.all():
            if t.update_status() == False:
                return False
        else:
            return [t.update_status() for t in self.subtasks.all()]

    def remove_subtask_by_result(self, res):
        for t in self.subtasks.all():
            if t.update_status() == res:
                t.delete()


class ObjetoThingiSubtask(models.Model):
    parent_task = models.ForeignKey(ObjetoThingi,on_delete=models.SET_NULL,null=True,related_name='subtasks')
    celery_id = models.CharField(max_length=100,null=True)

    def update_status(self):
        res = AsyncResult(self.celery_id)
        if res.ready():
            result = res.result
            return result
        else:
            return False

'''
Thingiverse tiene una estructura de subcategorias, en donde en algunos casos hay que hacer hasta 3
queries, para obtener la categoria padre de un objeto. Por eso, las cacheamos previamente
'''

class CategoriaThigi(models.Model):
    name = models.CharField(max_length=100,primary_key=True)
    parent = models.ForeignKey('self',on_delete=models.SET_NULL,null=True)

    def get_parent(self):
        p = self
        while p.parent:
             p = p.parent
        return p

'''
Clases de referencia external. Estos se utilizan para completar informacion de la DB, propia al repositorio en cuestion
'''

class AtributoExterno(models.Model):
    reference = models.OneToOneField('db.ReferenciaExterna', on_delete=models.CASCADE, related_name='thingiverse_attributes')
    license = models.CharField(max_length=200, null=True)
    like_count = models.IntegerField(default=0)
    download_count = models.IntegerField(default=0)
    added = models.DateTimeField(default=timezone.now)
    original_file_count = models.IntegerField(default=0)
    #Paso el filtro?
    filter_passed = models.BooleanField(default=True)


'''
Extension de ArchivoSTL, que agrega informacion requerida para los filtros
'''

class InformacionThingi(models.Model):
    file = models.OneToOneField('db.ArchivoSTL', on_delete=models.CASCADE, null=True)
    original_filename = models.CharField(max_length=300)
    date = models.DateTimeField(default=timezone.now,blank=True)
    thingi_id = models.IntegerField(default=0)
    #Paso el filtro?
    filter_passed = models.NullBooleanField(default=None)


'''
Clase de informacion de Mesh. Se utiliza para el filtro de archivos de una thing, y extiende a esta clase
'''

class InformacionMesh(models.Model):
    bounding_box_x = models.FloatField(default=0)
    bounding_box_y = models.FloatField(default=0)
    bounding_box_z = models.FloatField(default=0)
    area = models.FloatField(default=0)
    volume = models.FloatField(default=0)
    is_watertight = models.BooleanField(default=False)
    body_count = models.IntegerField(default=0)
    file = models.OneToOneField('db.ArchivoSTL', on_delete=models.CASCADE, null=True)

    @property
    def bounding_box(self):
        return [self.bounding_box_x, self.bounding_box_y, self.bounding_box_z]

    @property
    def fid(self):
        return self.file.id

    @staticmethod
    def informacion_mesh_de_archivo_stl(archivo_stl: modelos.ArchivoSTL):
        with archivo_stl.file.file as file:
            mesh = trimesh.load_mesh(file.open(mode='rb'),file_type='stl')
            file.close()
        mesh_data = InformacionMesh()
        mesh_data.bounding_box_x, mesh_data.bounding_box_y, mesh_data.bounding_box_z = mesh.bounding_box_oriented.primitive.extents
        mesh_data.area = mesh.area
        mesh_data.volume = mesh.volume
        mesh_data.is_watertight = mesh.is_watertight
        mesh_data.body_count = mesh.body_count
        mesh_data.file = archivo_stl
        mesh_data.save()

        return mesh_data


