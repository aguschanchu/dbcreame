from __future__ import absolute_import, unicode_literals
from celery import shared_task, group
from .models import *
import os
import requests
import random, string
from django.core.files import File
import time
from urllib.parse import urlparse, quote
import traceback
from django.conf import settings
import json
import urllib3
from urllib3.util import Retry
from urllib3 import PoolManager, ProxyManager, Timeout
from urllib3.exceptions import MaxRetryError, TimeoutError, ProxyError
import pickle
urllib3.disable_warnings()
from celery.task import control
from celery.exceptions import SoftTimeLimitExceeded, MaxRetriesExceededError
import dateutil.parser
from .filters.things_filter import *
from .filters.things_files_filter import thing_files_filter
from slaicer.models import GeometryModel, SliceJob
import numpy as np
import base64
from celery.utils.log import get_task_logger
import requests
logger = get_task_logger(__name__)

def get_connection_pool():
    retry_policy = Retry(total=5, backoff_factor=0.1, status_forcelist=[x for x in range(405, 501) if x not in [407]])
    timeout_policy = Timeout(read=10, connect=5)
    if settings.USE_SCAPOXY:
        http = ProxyManager('http://localhost:8888', retries= retry_policy, timeout = timeout_policy)
    else:
        http = PoolManager(retries= retry_policy, timeout = timeout_policy)
    return http


def adjust_proxy_scaling():
    headers = {'Authorization': base64.b64encode(str.encode(settings.SCRAPOXY_PASSWORD)), 'Content-type': 'application/json'}
    # Check for actual status
    try:
        r = requests.get('http://localhost:8889/api/scaling', headers=headers).json()
    except:
        raise ValueError("Error on connecting to proxy manager")
    if r['required'] == 0:
        payload = {"downscaleDelay": 30*60*1000, "min": 0, "max": settings.SCRAPOXY_MAX_SCALE, "required": 1}
        requests.patch(url='http://localhost:8889/api/scaling', data=json.dumps(payload), headers=headers)


class ProxyErrorCode(Exception):
    """ Used for error tracking """


@shared_task(queue='http',autoretry_for=(TypeError, ValueError), retry_backoff=True, max_retries=50, retry_jitter=True)
def request_from_thingi(url, content=False, params=''):
    global logger
    endpoint = settings.THINGIVERSE_API_ENDPOINT
    http = get_connection_pool()
    for _ in range(0, 60):
        k = ApiKey.get_api_key()
        if k is not None:
            for tries in range(1, 3):
                try:
                    if not content:
                        r = http.request('GET', endpoint+quote(url)+'?access_token='+k+params)
                        if r.status == 407:
                            raise ProxyError
                        r = json.loads(r.data.decode('utf-8'))
                    else:
                        r = http.request('GET', endpoint+quote(url)+'?access_token='+k+params)
                        if r.status == 407:
                            raise ProxyError
                        r = r.data
                    return r

                except (MaxRetryError, TimeoutError) as e:
                    if hasattr(e, 'reason'):
                        if type(e.reason) == ProxyError:
                            adjust_proxy_scaling()
                            time.sleep(10)
                    else:
                        # Por algun motivo celery no maneja bien estos errores. Por eso, los handleo, y re-raise otro tipo de error
                        logger.warning("Error al realizar request")
                        raise ValueError

                except (ProxyErrorCode, ProxyError):
                    adjust_proxy_scaling()
                    time.sleep(10)
                except json.decoder.JSONDecodeError:
                    raise ValueError
        else:
            time.sleep(1)
            print('No encontre API keys')
    else:
        traceback.print_exc()
        logger.error("Error al hacer la request ¿hay API keys disponibles?")
        raise ValueError("Error al hacer la request ¿hay API keys disponibles?")


@shared_task(queue='http',autoretry_for=(TypeError,ValueError,KeyError,MaxRetryError), retry_backoff=True, max_retries=50, retry_jitter=True)
def get_thing_categories_list(thingiid):
    endpoint = settings.THINGIVERSE_API_ENDPOINT
    rcat = request_from_thingi('things/{}/categories'.format(thingiid))
    result = []
    #Para cada una de las categorias, accedemos a la URL de esta
    for cat in rcat:
        if cat['url'].split(endpoint)[1] == "categories/other":
            result.append('Other')
        else:
            #Antes de buscar la categoria en Thingiverse, la tenemos cacheada?
            cache_search = CategoriaThigi.objects.filter(name=cat['name'])
            if cache_search:
                result.append(cache_search.first().get_parent().name)
            else:
                print("No encontre el resultado en cache: {}".format(cat['name']))
                print(cache_search)
                category_info = request_from_thingi(cat['url'].split(endpoint)[1])
                category_name = category_info['name']
                has_parent = 'parent' in category_info
                #Es una subcategoria? De ser así, accedemos a la padre
                while has_parent:
                    category_info = request_from_thingi(category_info['parent']['url'].split(endpoint)[1])
                    category_name = category_info['name']
                    has_parent = 'parent' in category_info
                #Guardamos el resultado de busqueda en el cache
                parent = CategoriaThigi.objects.get_or_create(name=category_name,parent=None)[0]
                if category_info['name'] != cat['name']:
                    CategoriaThigi.objects.get_or_create(name=cat['name'],parent=parent)
                result.append(category_name)
    return result

@shared_task(queue='http',autoretry_for=(TypeError,ValueError), retry_backoff=True, max_retries=100, retry_jitter=True)
def download_file(url, thingiid = None):
    http = get_connection_pool()
    path = 'tmp/'+''.join(random.choices(string.ascii_uppercase + string.digits, k=6)) + '.stl'
    try:
        with open(path,'wb') as file:
            file.write(http.request('GET', url).data)

    except (MaxRetryError, TimeoutError):
        # Por algun motivo celery no maneja bien estos errores. Por eso, los handleo, y re-raise otro tipo de error
        logger.warning("Error al realizar request")
        raise ValueError

    except:
        traceback.print_exc()
        logger.error("Error al descargar imagen, url {}".format(url))
        raise ValueError
    if thingiid != None:
        return (path, thingiid)
    else:
        return path

@shared_task(ignore_result=True, queue='low_priority')
def translate_tag(tag_id):
    modelos.Tag.objects.get(pk=tag_id).translate_es()

@shared_task(ignore_result=True, queue='low_priority')
def translate_category(cat_id):
    modelos.Categoria.objects.get(pk=cat_id).translate_es()

@shared_task(ignore_result=True, queue='low_priority')
def translate_name(object_id):
    modelos.Objeto.objects.get(pk=object_id).translate_es()


'''
A continuacion definimos un conjunto de tareas, que se ejecutaran en cadena para crear la thing
El esquema de ejecucion es el siguiente:
1) Descarga de informacion
2) Creacion de objeto
3) Descarga de Imagenes
4) Descarga de archivos y sliceo (de no ser una importacion parcial)
'''

def add_object_from_thingiverse_chain(thingiid, file_list = None, debug = True, partial = False, origin = None):
    #Descarga de informacion
    res = group([
    request_from_thingi.s('things/{}'.format(thingiid)),
    request_from_thingi.s('things/{}/tags'.format(thingiid)),
    get_thing_categories_list.s(thingiid),
    request_from_thingi.s('things/{}/images'.format(thingiid)),
    ])
    #Creacion de objeto a partir de informacion descargada
    res |= add_object.s(thingiid, partial, debug, origin)
    res |= download_images_task_group.s(partial, ObjetoThingi.priority_def(origin))
    if not partial:
        res |= add_files_to_thingiverse_object.s(file_list)
    return res

@shared_task(queue='http', bind=True,autoretry_for=(TypeError,ValueError,KeyError), retry_backoff=True, max_retries=50, retry_jitter=True)
def add_object(self, thingiverse_requests, thingiid, partial, debug, origin):
    global logger
    print("Iniciando descarga de "+str(thingiid))
    #Preparamos y enviamos todas las requests que necesitamos
    r = {}
    r['main'] = thingiverse_requests[0]
    r['tags'] = thingiverse_requests[1]
    r['categories'] = thingiverse_requests[2]
    r['img'] = thingiverse_requests[3]
    #Existe la thing?
    if "Not Found" in r['main'].values():
        raise ValueError("Thingiid invalida")
    # Procedemos a crear la thing
    ## Referencia Externa
    if modelos.ReferenciaExterna.objects.filter(repository='thingiverse',external_id=r['main']['id']).exists():
        #Pudimos obtener el modelo. eso significa que ya existe! Pero, está asociado a algo?
        for refext in modelos.ReferenciaExterna.objects.filter(repository='thingiverse',external_id=r['main']['id']):
            try:
                objeto = refext.objeto
                #Si no tenemos una exception, eso signfica que ya existe un objeto con esa referencia. Devolvemos eso
                print("WARNING: Referencia externa en DB ¿existe el modelo?")
                return (objeto.id, [j['sizes'][12]['url'] for j in r['img']])

            except modelos.Objeto.DoesNotExist:
                '''     
                Esta excepcion nos dice que existe la referencia, pero, no el objeto. El unico escenario donde podria estar pasando,
                es que haya una importacion  en curso de un objeto con la misma referencia. Por tal motivo, lentamos una excepcion,
                con fe en el el retry entre no ocurra esta excepcion (pues, la otra importacion finalizo)
                '''
                logger.error("Referencia hallada {}, pero no el objeto. Reintento por si se trata de alguna race condition".format(r['main']['id']))
                raise ValueError("Referencia hallada, pero, no el objeto")
            except MaxRetryError:
                return (None, [])
    else:
        #Procedemos a crear la ref externa
        referencia_externa = modelos.ReferenciaExterna.objects.create(repository='thingiverse', external_id=r['main']['id'])

    ## Atributos externos
    extattr = AtributoExterno.objects.get_or_create(reference=referencia_externa, license=r['main']['license'], like_count=r['main']['like_count'],
                                             download_count=r['main']['download_count'], added=dateutil.parser.parse(r['main']['added']),
                                             original_file_count=r['main']['file_count'])

    ## Autor
    autor = modelos.Autor.objects.get_or_create(username=r['main']['creator']['name'],name=r['main']['creator']['first_name'])[0]

    ## Categorias
    categorias = []
    ### Veamos que categorias existen, en la DB. Las que no, las creamos.
    for cat in r['categories']:
        categorias.append(modelos.Categoria.objects.get_or_create(name=cat)[0])

    ## Tags
    tags = []
    ### Veamos que categorias existen, en la DB. Las que no, las creamos.
    for tag in r['tags']:
        tags.append(modelos.Tag.objects.get_or_create(name=tag['name'])[0])

    ## Creacion de Objeto
    objeto = modelos.Objeto()

    ### Asignamos los campos
    objeto.author = autor
    objeto.name = r['main']['name']
    objeto.description = r['main']['description']
    objeto.external_id = referencia_externa
    objeto.origin = origin
    objeto.partial = True
    objeto.save()

    ### Asigamos categorias y tags
    for categoria in categorias:
        objeto.category.add(categoria)
    for tag in tags:
        objeto.tags.add(tag)

    return (objeto.id, [j['sizes'][12]['url'] for j in r['img']])

@shared_task()
def download_images_task_group(it, partial, priority):
    # Map a callback over an iterator and return as a group
    res = [translate_name.s(it[0])]
    #Una vez que se descargue la main image, podemos aplicar el filtro
    res.append(download_image.s(it[0],it[1].pop(0),True) | apply_thing_filter.s())
    for i in it[1]:
        res.append(download_image.s(it[0],i,False))
    g = group(res).apply_async(priority = priority)
    if partial:
        return (it[0],g.id)
    else:
        return (it[0],0)

@shared_task(queue='http',autoretry_for=(TypeError,ValueError), retry_backoff=True, max_retries=50, retry_jitter=True)
def download_image(objeto_id, url, main):
    objeto = modelos.Objeto.objects.get(pk=objeto_id)
    imagen = modelos.Imagen()
    path = download_file(url)
    with open(path,'rb') as file:
            image_file = File(file)
            imagen.photo.save(urlparse(url).path.split('/')[-1],image_file)
            imagen.main = main
            os.remove(path)
    imagen.object = objeto
    imagen.save()
    return objeto_id

@shared_task(autoretry_for=(TypeError,ValueError), retry_backoff=True, max_retries=50, retry_jitter=True)
def apply_thing_filter(object_id):
    objeto = modelos.Objeto.objects.get(pk=object_id)
    extattr = objeto.external_id.thingiverse_attributes

    thing = objeto
    if not license_filter(thing):
        print(1)
    if not image_filter(thing):
        print(2)
    if not category_filter(thing):
        print(3)
    if not likes_filter(thing):
        print(4)
    if not nsfw_filter(thing):
        print(5)
    if not keyword_filter(thing):
        print(6)
    if not thing_files_filter(thing):
        print(7)

    ### Ya con todos los datos, pasamos la thing por el filtro
    if objeto.origin != 'human':
        extattr.filter_passed = complete_filter_func(objeto)
        print('Resultado del filtro: {}'.format(extattr.filter_passed))
        if not extattr.filter_passed:
            objeto.hidden = True
            objeto.save(update_fields=['hidden'])
    else:
        extattr.filter_passed = True

    extattr.save(update_fields=['filter_passed'])

    return object_id

@shared_task(bind=True, max_retries=120, retry_backoff=True, retry_jitter=True)
def apply_thing_objects_filter(self, object_id):
    try:
        objeto = modelos.Objeto.objects.get(pk=object_id)
        extattr = objeto.external_id.thingiverse_attributes
    except:
        raise ValueError("Error al recuperar el archivo {}".format(object_id))

    # Necesitamos que esten todos los archivos cotizados, para lanzar este filtro
    for f in objeto.files.all():
        if not f.quote_ready():
            raise self.retry()

    file_list_modified = False
    # Aplicamos el filtro de archivos
    if objeto.origin != 'human':
        thing_files_filter(objeto)
        ## Borramos los archivos que no pasaron el filtro
        for f in objeto.files.all():
            if f.informacionthingi.filter_passed == False:
                f.object = None
                file_list_modified = True
                f.save(update_fields=['object'])

    # Tenemos que regenerar los sfb, si modificamos la lista de archivos
    if file_list_modified:
        objeto.modeloar.create_sfb(generate=True, force_generation=True)

    extattr.files_filter_passed = True
    extattr.save(update_fields=['files_filter_passed'])

    return object_id

@shared_task(bind=True, autoretry_for=(MaxRetryError, ConnectionResetError), retry_backoff=True, max_retries=120, retry_jitter=True)
def add_files_to_thingiverse_object(self, object_id, file_list = None, override = False, debug = True):
        allowed_extensions = ['.stl', '.obj']
        try:
            objeto = modelos.Objeto.objects.get(pk=object_id[0])
        except:
            raise ValueError("Error al recuperar el archivo {}".format(object_id[0]))
        task = ObjetoThingi.objects.filter(celery_id=self.request.id)[0]
        http = PoolManager(retries=Retry(total=20, backoff_factor=0.1, status_forcelist=list(range(400,501))))
        #Recuperamos el id del objeto
        if objeto.external_id != None:
            if objeto.external_id.repository != 'thingiverse':
                raise ValueError("El repositorio no es Thingiverse")
            thingiid = objeto.external_id.external_id
        else:
            raise ValueError("El objeto no tiene referencia externa")
        #Es un objeto parcial? De no ser asi, no hay nada que hacer
        if not objeto.partial:
            return (objeto.id, True)
        ## Archvos STL
        print("Preparando archivos")
        rfiles = request_from_thingi('things/{}/files'.format(thingiid))
        files_available_id = [a['id'] for a in rfiles]
        if file_list is None or file_list == []:
            file_list = files_available_id
        ### Nos pasaron una lista de archivos valida?
        for id in file_list:
            if id not in files_available_id:
                print("IDs disponibles:")
                print(files_available_id)
                objeto.delete()
                control.revoke(self.request.id)
                raise NameError("IDs de archivos invalida: "+id)
        '''
        Hay que descargar todos los archivos antes de continuar. Hay 3 escenarios posibles
        1) No inicio la descarga -> la inicio, y guardo el id del grupo de trabajo de descargas
        2) La descarga ya fue iniciada, pero, aun no termino algun archivo -> reintento la tarea
        3) La descarga ya finalizo -> Continuo con la cotizacion
        '''
        ### Tenemos una lista valida, procedemos a descargar los archivos
        if task.subtasks.count() == 0:
            print('Descargando lista de archivos:')
            print(file_list)
            archivos_link = []
            for id in file_list:
                for thing_file in rfiles:
                    if id == thing_file['id']:
                        name = thing_file['name']
                        if any(s in name.lower() for s in allowed_extensions):
                            download_url = thing_file['download_url']
                            st = download_file.s(download_url+'?access_token='+ApiKey.get_api_key(), thingiid = thing_file['id']).apply_async(priority = task.priority_get)
                            ObjetoThingiSubtask.objects.create(parent_task=task, celery_id=st.id)
            else:
                print("Los archivos no estan listos, comprobamos en 5s nuevamente")
                raise self.retry()

        ### Termino el grupo de trabajo?
        if task.update_subtask_status() == False:
            print("Los archivos no estan listos, comprobamos en 5s nuevamente")
            raise self.retry()



        ### Ok, termino. Agregamos los archivos al objeto, y continuamos
        archivos_link = task.update_subtask_status()
        print('Tenemos esta lista de archivos descargados:')
        print(archivos_link)
        for link in archivos_link:
            with open(link[0], 'rb') as file:
                #Guardamos los campos adicionales que requiere el filtro
                info = InformacionThingi()
                for f in rfiles:
                    if f['id'] == link[1]:
                        info.original_filename = f['name']
                        info.date = dateutil.parser.parse(f['date'])
                        info.save()
                        info.thingi_id = link[1]
                        break

                # Guardamos el STL
                geometrymodel = GeometryModel()
                geometrymodel.file.save('{repository}-{id}-{fid}.{extension}'.format(repository=objeto.external_id.repository,
                                                                               id=objeto.external_id.external_id,
                                                                               fid=link[1],
                                                                               extension=f['name'].split('.')[-1]), File(file))
                geometrymodel.save()
                archivo = modelos.ArchivoSTL(model=geometrymodel,
                                             time_as_a_function_of_scale=modelos.Polinomio.objects.create(),
                                             object=objeto)

            # Ejecutar tareas de cotizacion
            geometrymodel.create_orientation_result(priority=task.priority_get)
            geometrymodel.create_geometry_result(priority=task.priority_get)
            archivo.quote = SliceJob.objects.quote_object(geometrymodel, priority=task.priority_get)
            archivo.save()

            # Limpiamos archivos descargados, y enlazamos modelos
            info.file = archivo
            info.save()
            os.remove(link[0])
            task.remove_subtask_by_result(link)

            # Solicitamos cotizacion para armar el polinomio
            for scale in np.linspace(0.2, 2, 9):
                quote = SliceJob.objects.quote_object(geometrymodel, scale=scale, priority=task.priority_get)
                modelos.PolinomioPunto.objects.create(quote=quote,
                                                      scale=scale,
                                                      poly=archivo.time_as_a_function_of_scale)


        # Lanzamos el filtro de archivos
        apply_thing_objects_filter.s(objeto.id).apply_async(priority = task.priority_get)

        # Preparamos el modelo AR
        modelo_ar = modelos.ModeloAR()
        modelo_ar.object = objeto
        modelo_ar.save()
        modelo_ar.create_sfb(generate=True)

        # Le quitamos el flag de importacion parcial
        objeto.partial = False
        objeto.save(update_fields=['partial'])
        return (objeto.id, True)





def add_objects(max_things,start_page=0):
    #Funcion para popular la base de datos
    thing_counter = 0
    page_counter = start_page
    things_to_add = []
    while thing_counter < max_things:
        page_counter += 1
        try:
            r = request_from_thingi('/popular',False,'&page={}'.format(page_counter))
        except:
            r = []
            time.sleep(2)
        for item in r:
            try:
                if not modelos.ReferenciaExterna.objects.filter(external_id=item['id']).exists():
                    things_to_add.append(item['id'])
                    thing_counter += 1
            except:
                traceback.print_exc()
                time.sleep(2)
                print('Error al agregar objeto:')
        print('Contador: {}'.format(thing_counter))
    for x in things_to_add:
        try:
            ObjetoThingi.objects.create_object(x, partial=False, origin='popular')
        except:
            traceback.print_exc()
            time.sleep(2)
            print('Error al agregar objeto: {}'.format(item['id']))

def import_from_thingiverse_parser(base):
    '''
    A partir de un BufferedReader de un archivo de pickle, importa las things
    '''
    base = pickle.load(base)
    for thing in base:
        try:
            ObjetoThingi.objects.create_object(thing['thing_id'], partial=False, origin='human', file_list=thing['thing_files_id'])
        except:
            traceback.print_exc()
            time.sleep(2)
            print('Error al agregar objeto: {}'.format(thing['thing_id']))




'''
from db.tools.import_from_thingi import *
from db.models import *
import pickle
with open('things_ids_complete.db','rb') as base:
    import_from_thingiverse_parser(base)
'''
