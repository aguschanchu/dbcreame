from django.db import models
from django.contrib.postgres.fields import ArrayField
from celery.result import AsyncResult
from db import models as modelos
from . import tasks
import datetime
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
        object = self.create(external_id=external_id, file_list=file_list, partial=partial)
        # Ejecutamos la tarea
        job = tasks.add_object_from_thingiverse_chain(thingiid=external_id, file_list=file_list, partial=partial, origin=origin).apply_async(max_retries=300)
        object.celery_id = job.id
        object.save(update_fields=["celery_id"])
        return object

    def update_object(self, object_id, file_list=None, update_object=True, partial=False, subtask_ids_list = None):
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
    update_object = models.BooleanField(default=False)

    objects = ObjetoThingiManager()

    def update_status(self):
        res = AsyncResult(self.celery_id)
        self.status = res.state
        if res.ready():
            result = res.result
            self.object_id = modelos.Objeto.objects.get(pk=result[0])
            # Tiene imagen principal?
            if not self.object_id.main_image:
                self.status = 'STARTED'
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
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self',on_delete=models.SET_NULL,null=True)

    def get_parent(self):
        p = self
        while not p.parent:
             p = p.parent
        return actual_parent
