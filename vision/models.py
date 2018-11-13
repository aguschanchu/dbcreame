from django.db import models
from . import tasks
from celery.result import AsyncResult
from django.utils import timezone
import uuid

class ImagenVisionAPIManager(models.Manager):
    def create_object(self,image,celery_id=None,status=None,search_results=None,subtasks=None,tag_search_result=None):
        object = self.create(image=image)
        # Ejecutamos la tarea
        job = tasks.process_image.delay(object.id)
        object.celery_id = job.id
        object.status = 'QUEUED'
        object.save(update_fields=["celery_id","status"])
        return object

class ImagenVisionAPI(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    image = models.ImageField(upload_to='images/visionapi/')
    celery_id = models.CharField(max_length=100,blank=True,null=True)
    status = models.CharField(max_length=50,blank=True,null=True)
    created = models.DateTimeField(default=timezone.now)
    finished = models.DateTimeField(null=True)

    objects = ImagenVisionAPIManager()

    @property
    def search_results(self):
        self.filter_duplicates()
        return self.search_result.all().filter(object__isnull=False)

    @property
    def query_time(self):
        return self.finished - self.created

    def filter_duplicates(self):
        #Hay duplicados? (SQL nos va decir mas rapido)
        if self.search_result.all().filter(object__isnull=False).count() == self.search_result.all().filter(object__isnull=False).values_list('object',flat=True).distinct().count():
            print("No hay duplicados")
            return True
        unique_ids = []
        for o in self.search_result.all().filter(object__isnull=False):
            if o.object.id in unique_ids:
                o.delete()
            else:
                unique_ids.append(o.object.id)

    def update_status(self):
        res = AsyncResult(self.celery_id)
        #Termino la busqueda?
        if not res.ready():
            return False
        #OK, si. Tiene alguna subtarea pendiente? De ser asi, actualizamos el estado de las mismas
        for s in self.search_result.all():
            if not s.ready():
                return False
        else:
            self.status = 'SUCCESS'
            if not self.finished:
                self.finished = timezone.now()
            self.save(update_fields=['status', 'finished'])


class ImagenVisionApiResult(models.Model):
    search = models.ForeignKey(ImagenVisionAPI, on_delete=models.CASCADE, related_name='search_result')
    label_score = models.FloatField(default=0)
    score = models.FloatField(default=0)
    object = models.ForeignKey('db.Objeto', blank=True, on_delete=models.CASCADE, null=True)
    subtask = models.ForeignKey('thingiverse.ObjetoThingi', null=True, on_delete=models.CASCADE)

    def update_score(self):
        self.score = self.object.score * self.label_score**20 if self.object != None else 0
        self.save(update_fields=['score'])

    def ready(self):
        if self.object != None or self.subtask == None:
            if self.score == 0:
                self.update_score()
            return True
        self.subtask.update_status()
        if self.subtask.status == 'SUCCESS':
            #Termino la subtarea, actualizamos el object linkeado
            self.object = self.subtask.object_id
            #Paso el filtro este objeto?
            if not self.object.external_id.thingiverse_attributes.filter_passed:
                self.subtask = None
                self.object = None
            self.save()
            self.update_score()
            return True
        elif self.subtask.status == 'FAILURE':
            self.delete()
            return False
        else:
            return False

class TagSearchResult(models.Model):
    tag = models.CharField(max_length=100)
    score = models.FloatField(default=0)
    parent = models.ForeignKey(ImagenVisionAPI,related_name='tag_search_result',on_delete=models.CASCADE)
