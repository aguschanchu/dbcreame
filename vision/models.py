from django.db import models
from . import tasks
from celery.result import AsyncResult
import uuid

class SearchResult(models.model):
    tag = models.CharField(max_length=100)
    score = models.FloatField(default=0)
    parent = models.ForeignKey(ImagenVisionAPI)

class ImagenVisionAPIManager(models.Manager):
    def create_object(self,image,celery_id=None,status=None,search_results=None,subtasks=None):
        object = self.create(image=image)
        # Ejecutamos la tarea
        job = tasks.process_image.delay(object.id)
        object.celery_id = job.id
        object.save(update_fields=["celery_id"])
        return object

class ImagenVisionAPI(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    image = models.ImageField(upload_to='images/visionapi/')
    celery_id = models.CharField(max_length=100,blank=True,null=True)
    search_results = models.ManyToManyField('db.Objeto',blank=True)
    subtasks = models.ManyToManyField('thingiverse.ObjetoThingi',blank=True)
    status = models.CharField(max_length=50,blank=True,null=True)

    objects = ImagenVisionAPIManager()

    def update_status(self):
        res = AsyncResult(self.celery_id)
        #Termino la busqueda?
        if not res.ready():
            return False
        #OK, si. Tiene alguna subtarea pendiente? De ser asi, actualizamos el estado de las mismas
        for s in self.subtasks.all():
            s.update_status()
            if not s.status == 'SUCCESS':
                return False
            else:
                #Oh, que bueno, una subtarea que termino. Agregamos el resultado a search_results
                self.search_results.add(s.object_id)
        else:
            self.status = 'SUCCESS'
            self.save(update_fields=['status'])
