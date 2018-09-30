from django.db import models
from django.contrib.postgres.fields import ArrayField
from django_celery_results.models import TaskResult
from db import models as modelos
from . import tasks
import datetime

'''
Tenemos un limite de 300/5', queremos monitorear cada key, para no pasarnos
'''

class QueryEvent(models.Model):
    date = models.DateTimeField(auto_now_add=True)

class ApiKey(models.Model):
    quota = 290
    quota_interval = 5*60
    key = models.CharField(max_length=100)
    meter = models.ManyToManyField(QueryEvent)

    def clean(self):
        #¿Es valida?
        r = requests.get(settings.THINGIVERSE_API_ENDPOINT+'things/763622?access_token='+str(self.key)).json()
        if 'Unauthorized' in r.values():
            raise ValidationError('API key invalida')

    def make_query(self):
        event = QueryEvent.objects.create()
        self.meter.add(event)

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

class ObjetoThingiManager(models.Manager):
    def create_object(self, external_id, file_list=None, partial=False, origin=None):
        object = self.create(external_id=external_id, file_list=file_list, partial=partial)
        # Ejecutamos la tarea
        job = tasks.add_object_from_thingiverse_chain(thingiid=external_id, file_list=file_list, partial=partial, origin=origin).apply_async()
        object.celery_id = job.id
        object.save()
        return object

class ObjetoThingi(models.Model):
    estados = (
        ('processing', 'Procesando'),
        ('error', 'Error'),
        ('finished', 'Finalizado'),
    )
    external_id = models.IntegerField()
    #Lista de archivos thing a tener en cuenta. Puede ser nulo (y por lo tanto, descarga todos) o una lista
    file_list = ArrayField(models.CharField(max_length=30, blank=True),null=True)
    status = models.CharField(choices=estados,max_length=300,blank=True,default="processing")
    celery_id = models.CharField(max_length=100,blank=True)
    object_id = models.ForeignKey('db.Objeto',null=True,on_delete=models.SET_NULL)
    partial = models.BooleanField(default=True)

    objects = ObjetoThingiManager()
    def update_status(self):
        res = TaskResult.objects.filter(task_id=celery_id)
        if res.count() == 0:
            self.status = 'processing'
        else:
            try:
                self.object_id = modelos.Objeto.objects.get(pk=res[0])
                self.status = 'finished'
            except:
                self.status = 'error'
        self.save()
