from .. import models as modelos
from django.db import models
import datetime
import requests
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.files.base import ContentFile
import time
from urllib.parse import urlparse
import traceback
from django.conf import settings
import json
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

def request_from_thingi(url,content=False):
    endpoint = 'https://api.thingiverse.com/'
    for _ in range(0,60):
        k = get_api_key()
        if k != None:
            if not content:
                r = requests.get(endpoint+url+'?access_token='+k).json()
            else:
                r = requests.get(endpoint+url+'?access_token='+k).content
            return r
    else:
        traceback.print_exc()
        raise ValueError("Error al hacer la request ¿hay API keys disponibles?")

'''
Ahora que ya tenemos control sobre las keys, descargamos el objeto
'''

def add_object_from_thingiverse(thingiid,file_list = None):
    r = request_from_thingi('things/{}'.format(thingiid))
    #Existe la thing?
    if "Not Found" in r.values():
        raise ValueError("Thingiid invalida")
    # Procedemos a crear la thing
    ## Referencia Externa
    if modelos.ReferenciaExterna.objects.filter(repository='thingiverse',external_id=r['id']).exists():
        #Pudimos obtener el modelo. eso significa que ya existe!
        raise ValueError("Referencia externa en DB ¿existe el modelo?")
    else:
        #Procedemos a crear la ref externa
        referencia_externa = modelos.ReferenciaExterna.objects.create(repository='thingiverse',external_id=r['id'])
    ## Autor
    autor = modelos.Autor.objects.get_or_create(username=r['creator']['name'],name=r['creator']['first_name'])[0]
    ## Categorias
    rcat = request_from_thingi('things/{}/categories'.format(thingiid))
    categorias = []
    ### Veamos que categorias existen, en la DB. Las que no, las creamos.
    for cat in rcat:
        categorias.append(modelos.Categoria.objects.get_or_create(name=cat['name'])[0])
    ## Tags
    rtag = request_from_thingi('things/{}/tags'.format(thingiid))
    tags = []
    ### Veamos que categorias existen, en la DB. Las que no, las creamos.
    for tag in rtag:
        tags.append(modelos.Tag.objects.get_or_create(name=tag['name'])[0])
    ## Imagenes
    rimg = request_from_thingi('things/{}/images'.format(thingiid))
    ###Imagen principal
    url = rimg[0]['sizes'][12]['url']
    try:
        rmain = requests.get(url)
    except:
        raise ValueError("Error al descargar imagen")
    main_image = ContentFile(rmain.content)
    main_image_name = urlparse(url).path.split('/')[-1]
    ###Imagenes adicionales
    imagenes = []
    for j in range(1,len(rimg)):
        url = rimg[j]['sizes'][12]['url']
        name = urlparse(url).path.split('/')[-1]
        try:
            rimg_src = requests.get(url)
        except:
            raise ValueError("Error al descargar imagen")
        imagen = modelos.Imagen()
        imagen.photo.save(name,ContentFile(rimg_src.content))
        imagenes.append(imagen)

    ## Archvos STL
    rfiles = request_from_thingi('things/{}/files'.format(thingiid))
    files_available_id = [a['id'] for a in rfiles]
    if file_list == None:
        file_list = files_available_id
    ### Nos pasaron una lista de archivos valida?
    for id in file_list:
        if id not in files_available_id:
            raise ValueError("IDs de archivos invalida: "+id)
    ### Tenemos una lista valida, procedemos a descargar los archivos
    print(file_list)
    archivos = []
    for id in file_list:
        for thing_file in rfiles:
            if id == thing_file['id']:
                name = thing_file['name']
                if '.stl' in name.lower():
                    try:
                        rfile_src = requests.get(thing_file['default_image']['url'])
                    except:
                        raise ValueError("Error al descargar archivo")
                    archivo = modelos.ArchivoSTL()
                    archivo.file.save(name,ContentFile(rfile_src.content))
                    archivos.append(archivo)
    ### Tenemos los archivos descargados. Necesitamos completar su tiempo de imp, peso, dimensiones
    slicer_jobs_ids = {}
    slicer_jobs_ids_poly = {}
    for archivo in archivos:
        archivos_r = {'file': archivo.file.open(mode='rb')}
        rf = requests.post(settings.SLICER_API_ENDPOINT, files = archivos_r)
        archivos_r = {'file': archivo.file.open(mode='rb')}
        rfp = requests.post(settings.SLICER_API_ENDPOINT+'tiempo_en_funcion_de_escala/', files = archivos_r)
        archivo.file.close
        print(rfp.content)
        #Parseamos la id de trabajo
        slicer_jobs_ids[archivo] = rf.json()['id']
        slicer_jobs_ids_poly[archivo] = rfp.json()['id']
    print(slicer_jobs_ids, slicer_jobs_ids_poly)
    ### Esperamos 300s a que haga todos los trabajos
    poly_f, slice_f = False, False
    for _ in range(0,300):
        #Termino con el calculo de polinomios?
        if not poly_f:
            for job_id in slicer_jobs_ids_poly.values():
                estado = requests.get(settings.SLICER_API_ENDPOINT+'tiempo_en_funcion_de_escala/status/{}/'.format(job_id)).json()['estado']
                if estado != '200':
                    break
            else:
                poly_f = True
        #Y con el calculo de pesos (aka sliceo comun)?
        if not slice_f:
            for job_id in slicer_jobs_ids.values():
                estado = requests.get(settings.SLICER_API_ENDPOINT+'status/{}/'.format(job_id)).json()['estado']
                if estado != '200':
                    break
            else:
                slice_f = True
        if slice_f and poly_f:
            break
        time.sleep(1)
    else:
        #Pasaron los 300s, y no termino de slicear
        print(slicer_jobs_ids.values(), slicer_jobs_ids_poly.values())
        raise ValueError("Timeout al solicitar el sliceo de los modelos")
    ### Completamos todos los datos de los archivos
    for archivo in archivos:
        #Creamos el polinomio
        rf = json.loads(requests.get(settings.SLICER_API_ENDPOINT+'tiempo_en_funcion_de_escala/status/{}/'.format(slicer_jobs_ids_poly[archivo])).json()['poly'])
        polinomio = modelos.Polinomio()
        polinomio.a2 = rf[0]
        polinomio.a3 = rf[1]
        polinomio.a4 = rf[2]
        polinomio.a5 = rf[3]
        polinomio.save()
        #Establecemos los coeficientes y guardamos
        rf = requests.get(settings.SLICER_API_ENDPOINT+'status/{}/'.format(slicer_jobs_ids[archivo])).json()
        archivo.printing_time_default = rf['tiempo_estimado']
        archivo.size_x_default = rf['size_x']
        archivo.size_y_default = rf['size_y']
        archivo.size_z_default = rf['size_z']
        archivo.weight_default = rf['peso']
        archivo.tiempo_en_funcion_de_escala = polinomio
        archivo.save()

    ## Creacion de Objeto
    objeto = modelos.Objeto()

    ### Asignamos los campos
    print(autor)
    objeto.author = autor
    objeto.name = r['name']
    objeto.description = r['description']
    objeto.external_id = referencia_externa
    objeto.main_image.save(main_image_name,main_image)
    objeto.save()

    for imagen in imagenes:
        objeto.images.add(imagen)
    for archivo in archivos:
        objeto.files.add(archivo)
    for categoria in categorias:
        objeto.category.add(categoria)
    for tag in tags:
        objeto.tags.add(tag)

    objeto.save()















'''
from db.tools.import_from_thingi import *
from db.models import *
a = ***REMOVED***
add_object_from_thingiverse(1278865)
p = QueryPool.objects.create()
p.keys.add(a)
p.get_key()

def dowload_thing(thingiid,file_list):
'''
