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
import urllib3
from urllib3.util import Retry
from urllib3 import PoolManager
urllib3.disable_warnings()

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

def request_from_thingi(url,content=False,params=''):
    endpoint = settings.THINGIVERSE_API_ENDPOINT
    http = PoolManager(retries=Retry(total=5, status_forcelist=[500]))
    for _ in range(0,60):
        k = get_api_key()
        if k != None:
            if not content:
                r = json.loads(http.request('GET',endpoint+url+'?access_token='+k+params).data.decode('utf-8'))
            else:
                r = http.request('GET',endpoint+url+'?access_token='+k+params).data
            return r
        time.sleep(1)
    else:
        traceback.print_exc()
        print("URL que intente acceder: "+endpoint+url+'?access_token='+str(k))
        raise ValueError("Error al hacer la request ¿hay API keys disponibles?")

'''
Ahora que ya tenemos control sobre las keys, nos preparamos para descargar el objeto
'''

def get_thing_categories_list(thingiid):
    http = PoolManager(retries=Retry(total=5, status_forcelist=[500]))
    endpoint = settings.THINGIVERSE_API_ENDPOINT
    rcat = request_from_thingi('things/{}/categories'.format(thingiid))
    result = []
    #Para cada una de las categorias, accedemos a la URL de esta
    for cat in rcat:
        category_info = request_from_thingi(cat['url'].split(endpoint)[1])
        category_name = category_info['name']
        has_parent = 'parent' in category_info
        #Es una subcategoria? De ser así, accedemos a la padre
        while has_parent:
            category_info = request_from_thingi(category_info['parent']['url'].split(endpoint)[1])
            category_name = category_info['name']
            has_parent = 'parent' in category_info
        result.append(category_name)
    return result

def add_object_from_thingiverse(thingiid,file_list = None, override = False, debug = True):
    http = PoolManager(retries=Retry(total=5, status_forcelist=[500]))
    print("Iniciando descarga de "+str(thingiid))
    r = request_from_thingi('things/{}'.format(thingiid))
    #Existe la thing?
    if "Not Found" in r.values():
        raise ValueError("Thingiid invalida")
    # Procedemos a crear la thing
    ## Referencia Externa
    if modelos.ReferenciaExterna.objects.filter(repository='thingiverse',external_id=r['id']).exists():
        #Pudimos obtener el modelo. eso significa que ya existe! Pero, está asociado a algo?
        for refext in modelos.ReferenciaExterna.objects.filter(repository='thingiverse',external_id=r['id']):
            try:
                refext.objeto
                #Si no tenemos una exception, eso signfica que...
                raise ValueError("Referencia externa en DB ¿existe el modelo?")
            except modelos.Objeto.DoesNotExist:
                referencia_externa = refext
    else:
        #Procedemos a crear la ref externa
        referencia_externa = modelos.ReferenciaExterna.objects.create(repository='thingiverse',external_id=r['id'])
    ## Autor
    autor = modelos.Autor.objects.get_or_create(username=r['creator']['name'],name=r['creator']['first_name'])[0]
    ## Categorias
    categorias = []
    ### Veamos que categorias existen, en la DB. Las que no, las creamos.
    for cat in get_thing_categories_list(thingiid):
        categorias.append(modelos.Categoria.objects.get_or_create(name=cat)[0])
    ### Pedimos que traduzca las categorias. Si ya existia, no pasa nada, ya que se ejecuta solo si no fue traducida
    for cat in categorias:
        cat.translate_es()
    ## Tags
    rtag = request_from_thingi('things/{}/tags'.format(thingiid))
    tags = []
    ### Veamos que categorias existen, en la DB. Las que no, las creamos.
    for tag in rtag:
        tags.append(modelos.Tag.objects.get_or_create(name=tag['name'])[0])
    ### Traduccion de tags
    for tag in tags:
        tag.translate_es()
    ## Imagenes
    print("Descargando imagenes")
    rimg = request_from_thingi('things/{}/images'.format(thingiid))
    ###Imagen principal
    url = rimg[0]['sizes'][12]['url']
    try:
        rmain = http.request('GET', url).data
    except:
        raise ValueError("Error al descargar imagen")
    main_image = ContentFile(rmain)
    main_image_name = urlparse(url).path.split('/')[-1]
    ###Imagenes adicionales
    imagenes = []
    for j in range(1,len(rimg)):
        url = rimg[j]['sizes'][12]['url']
        name = urlparse(url).path.split('/')[-1]
        try:
            rimg_src = http.request('GET', url).data
        except:
            raise ValueError("Error al descargar imagen")
        imagen = modelos.Imagen()
        imagen.photo.save(name,ContentFile(rimg_src))
        imagenes.append(imagen)

    ## Archvos STL
    print("Preparando archivos")
    rfiles = request_from_thingi('things/{}/files'.format(thingiid))
    files_available_id = [a['id'] for a in rfiles]
    if file_list == None:
        file_list = files_available_id
    else:
        file_list = json.loads(file_list)
    ### Nos pasaron una lista de archivos valida?
    for id in file_list:
        if id not in files_available_id:
            raise ValueError("IDs de archivos invalida: "+id)
    ### Tenemos una lista valida, procedemos a descargar los archivos
    print('Descargando lista de archivos:')
    print(file_list)
    archivos = []
    for id in file_list:
        for thing_file in rfiles:
            if id == thing_file['id']:
                name = thing_file['name']
                if '.stl' in name.lower():
                    try:
                        download_url = thing_file['download_url']
                        rfile_src = http.request('GET', thing_file['download_url']+'?access_token='+get_api_key()).data
                    except:
                        print(thing_file)
                        raise ValueError("Error al descargar archivo")
                    archivo = modelos.ArchivoSTL()
                    archivo.file.save(referencia_externa.repository+'-'+str(referencia_externa.external_id)+'-'+name,ContentFile(rfile_src))
                    archivos.append(archivo)
    ### Tenemos los archivos descargados. Necesitamos completar su tiempo de imp, peso, dimensiones
    print("Ejecutando trabajos de sliceo")
    slicer_jobs_ids = {}
    slicer_jobs_ids_poly = {}
    for archivo in archivos:
        archivos_r = {'file': archivo.file.open(mode='rb')}
        rf = requests.post(settings.SLICER_API_ENDPOINT, files = archivos_r)
        archivos_r = {'file': archivo.file.open(mode='rb')}
        parametros = {'escala_inicial':'0.2','escala_final':'1.2','escala_paso':'0.2'}
        rfp = requests.post(settings.SLICER_API_ENDPOINT+'tiempo_en_funcion_de_escala/', files = archivos_r, data = parametros)
        archivo.file.close
        #Parseamos la id de trabajo
        slicer_jobs_ids[archivo] = rf.json()['id']
        slicer_jobs_ids_poly[archivo] = rfp.json()['id']
    ### Esperamos 600s a que haga todos los trabajos
    print("Trabajos inicializados")
    poly_f, slice_f = False, False
    for _ in range(0,600):
        if debug and _%60==0:
            print("---------ID-------------------------ESTADO-----------")
        #Termino con el calculo de polinomios?
        if not poly_f:
            for job_id in slicer_jobs_ids_poly.values():
                estado = requests.get(settings.SLICER_API_ENDPOINT+'tiempo_en_funcion_de_escala/status/{}/'.format(job_id)).json()['estado']
                if debug and _%60==0:
                    print("          {}                      {}".format(job_id,estado))
                if int(estado) >= 300:
                    print("Hubo un error de sliceo, el identificador de trabajo es {}, con estado {}".format(job_id,estado))
                    raise ValueError("Slicing error")
                if estado != '200':
                    break
            else:
                poly_f = True
        #Y con el calculo de pesos (aka sliceo comun)?
        if not slice_f:
            for job_id in slicer_jobs_ids.values():
                estado = requests.get(settings.SLICER_API_ENDPOINT+'status/{}/'.format(job_id)).json()['estado']
                if debug and _%60==0:
                    print("          {}                      {}".format(job_id,estado))
                if int(estado) >= 300:
                    print("Hubo un error de sliceo, el identificador de trabajo es {}, con estado {}".format(job_id,estado))
                    raise ValueError("Slicing error")
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
    print("Creacion de objeto")
    for archivo in archivos:
        #Creamos el polinomio
        rf = json.loads(requests.get(settings.SLICER_API_ENDPOINT+'tiempo_en_funcion_de_escala/status/{}/'.format(slicer_jobs_ids_poly[archivo])).json()['poly'])
        polinomio = modelos.Polinomio()
        polinomio.a0 = rf[3]
        polinomio.a1 = rf[2]
        polinomio.a2 = rf[1]
        polinomio.a3 = rf[0]
        polinomio.save()
        #Establecemos los coeficientes y guardamos
        rf = requests.get(settings.SLICER_API_ENDPOINT+'status/{}/'.format(slicer_jobs_ids[archivo])).json()
        archivo.printing_time_default = rf['tiempo_estimado']
        archivo.size_x_default = rf['size_x']
        archivo.size_y_default = rf['size_y']
        archivo.size_z_default = rf['size_z']
        archivo.weight_default = rf['peso']
        archivo.time_as_a_function_of_scale = polinomio
        archivo.save()

    ## Creacion de Objeto
    objeto = modelos.Objeto()

    ### Asignamos los campos
    objeto.author = autor
    objeto.name = r['name']
    objeto.description = r['description']
    objeto.external_id = referencia_externa
    objeto.main_image.save(main_image_name,main_image)

    for categoria in categorias:
        objeto.category.add(categoria)
    for tag in tags:
        objeto.tags.add(tag)

    objeto.save()

    #Linkeamos los ForeignKey antes creados al objeto creado
    for imagen in imagenes:
        imagen.object = objeto
        imagen.save()
    for archivo in archivos:
        archivo.object = objeto
        archivo.save()

    modelo_ar = modelos.ModeloAR()
    modelo_ar.object = objeto
    modelo_ar.save()

    #Preparamos el modelo AR
    modelo_ar.create_sfb(generate=True)
    modelo_ar.save()

    #Traducimos el nombre
    objeto.translate_es()
    objeto.save()



def add_objects(max_things,start_page=0):
    #Funcion para popular la base de datos
    thing_counter = 0
    page_counter = start_page
    while thing_counter < max_things:
        page_counter += 1
        r = request_from_thingi('/popular',False,'&page={}'.format(page_counter))
        for item in r:
            try:
                add_object_from_thingiverse(item['id'])
                thing_counter += 1
            except:
                traceback.print_exc()
                time.sleep(2)
                print('Error al agregar objeto: {}'.format(item['id']))
        print('Contador: {}'.format(thing_counter))






'''
from db.tools.import_from_thingi import *
from db.models import *
***REMOVED***
***REMOVED***
***REMOVED***
***REMOVED***
add_objects(10)

def dowload_thing(thingiid,file_list):
'''
