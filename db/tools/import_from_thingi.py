from .. import models as modelos
from django.db import models
import datetime
import requests
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import time

print(modelos)
'''
Tenemos un limite de 300/5', queremos monitorear cada key, para no pasarnos
'''

class QueryEvent(models.Model):
    date = models.DateTimeField(auto_now_add=True)

class ApiKey(models.Model):
    endpoint = 'api.thingiverse.com'
    quota = 5
    quota_interval = 20
    key = models.CharField(max_length=100)
    meter = models.ManyToManyField(QueryEvent)

    def clean(self):
        #¿Es valida?
        r = requests.get('https://api.thingiverse.com/things/763622?access_token='+str(self.key)).json()
        if 'Unauthorized' in r.values():
            raise ValidationError(_('API key invalida'))

    def make_query(self):
        event = QueryEvent.objects.create()
        self.meter.add(event)

    def available(self):
        #Actualizamos la tabla de meters:
        for event in self.meter.all():
            if (datetime.datetime.now(datetime.timezone.utc)-event.date).seconds > self.quota_interval:
                event.delete()
        if len(self.meter.all()) < self.quota:
            return True
        else:
            return False


def get_api_key():
    for key in ApiKey.objects.all():
        if key.available():
            key.make_query()
            return key.key
        else:
            return None

'''
Ahora que ya tenemos control sobre las keys, descargamos el objeto
'''

def add_object_from_thingiverse(thingiid,file_list = None):
    for _ in range(0,60):
        k = get_api_key()
        if k != None:
            r = requests.get('https://api.thingiverse.com/things/{}?access_token={}'.format(thingiid,k)).json()
            break
    else:
        raise ValueError("Error al hacer la request ¿hay API keys disponibles?")
    #Existe la thing?
    if "Not Found" in r.values():
        raise ValueError("Thingiid invalida")
    # Procedemos a crear la thing
    ## Autor
    ### ¿Existe el autor?
    try:
        autor = modelos.Autor.objects.get(username=r['creator']['name'])
    ### No existe, creamos el autor
    except:
        autor = modelos.Autor.objects.create(username=r['creator']['name'],name=r['creator']['first_name'])
    ## Categorias
    for _ in range(0,60):
        k = get_api_key()
        if k != None:
            rcat = requests.get('https://api.thingiverse.com/things/{}/categories?access_token={}'.format(thingiid,k)).json()
            break
    else:
        raise ValueError("Error al hacer la request ¿hay API keys disponibles?")




'''
from db.tools.import_from_thingi import *
from db.models import *
a = ***REMOVED***
add_object_from_thingiverse(763622)
p = QueryPool.objects.create()
p.keys.add(a)
p.get_key()

def dowload_thing(thingiid,file_list):
'''
