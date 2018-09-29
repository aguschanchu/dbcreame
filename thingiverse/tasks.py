from __future__ import absolute_import, unicode_literals
from celery import shared_task
from .models import ApiKey
from db import models as modelos
from django.db import models
from thingiverse.models import *
import datetime
import os
import requests
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.files import File
import time
from urllib.parse import urlparse
import traceback
from django.conf import settings
import json
import urllib3
from urllib3.util import Retry
from urllib3 import PoolManager
import pickle
urllib3.disable_warnings()
from google.cloud import translate

@shared_task
def request_from_thingi(url,content=False,params=''):
    endpoint = settings.THINGIVERSE_API_ENDPOINT
    http = PoolManager(retries=Retry(total=5, status_forcelist=[500]))
    for _ in range(0,60):
        k = ApiKey.get_api_key()
        if k != None:
            if not content:
                r = json.loads(http.request('GET',endpoint+url+'?access_token='+k+params).data.decode('utf-8'))
            else:
                r = http.request('GET',endpoint+url+'?access_token='+k+params).data
            return r
        time.sleep(1)
        print('No encontre API keys')
    else:
        traceback.print_exc()
        print("URL que intente acceder: "+endpoint+url+'?access_token='+str(k))
        raise ValueError("Error al hacer la request ¿hay API keys disponibles?")

@shared_task
def get_thing_categories_list(thingiid):
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

@shared_task
def download_file(url):
    http = PoolManager(retries=Retry(total=5, status_forcelist=[500]))
    name = urlparse(url).path.split('/')[-1]
    path = 'tmp/'+''.join(random.choices(string.ascii_uppercase + string.digits, k=6)) + name
    try:
        with open(path,'wb') as file:
            file.write(http.request('GET', url).data)
    except:
        print("Error al descargar imagen")
        return None
    return path

@shared_task
def add_object_from_thingiverse(thingiid,file_list = None, override = False, debug = True, partial = False):
    if debug:
        t = time.time()
    print("Iniciando descarga de "+str(thingiid))
    #Preparamos y enviamos todas las requests que necesitamos
    r = {}
    r['main'] = request_from_thingi.delay('things/{}'.format(thingiid))
    r['tags'] = request_from_thingi.delay('things/{}/tags'.format(thingiid))
    r['categories'] = get_thing_categories_list.delay(thingiid)
    r['img'] = request_from_thingi.delay('things/{}/images'.format(thingiid))
    #Esperamos a que hayan finalizado las necesarias
    for key in r.keys():
        r[key] = r[key].get()
    if debug:
        print("Tiempo de requests: {}".format(time.time()-t))
        t = time.time()
    #Existe la thing?
    if "Not Found" in r['main'].values():
        raise ValueError("Thingiid invalida")
    # Procedemos a crear la thing
    ## Referencia Externa
    if modelos.ReferenciaExterna.objects.filter(repository='thingiverse',external_id=r['main']['id']).exists():
        #Pudimos obtener el modelo. eso significa que ya existe! Pero, está asociado a algo?
        for refext in modelos.ReferenciaExterna.objects.filter(repository='thingiverse',external_id=r['main']['id']):
            try:
                refext.objeto
                #Si no tenemos una exception, eso signfica que...
                raise ValueError("Referencia externa en DB ¿existe el modelo?")
            except modelos.Objeto.DoesNotExist:
                referencia_externa = refext
    else:
        #Procedemos a crear la ref externa
        referencia_externa = modelos.ReferenciaExterna.objects.create(repository='thingiverse',external_id=r['main']['id'])
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

    if debug:
        print("Tiempo de creacion de objetos {}".format(time.time()-t))
        t = time.time()
    ## Traduccion de tags y categorias
    if not partial:
        translate_client = translate.Client()
        ### Tags
        if len(tags) > 0:
            translation = translate_client.translate([tag.name for tag in tags],source_language='en',target_language='es')
            for i in range(0,len(translation)):
                tags[i].name_es = translation[i]['translatedText']
                tags[i].save()
        ### Categorias
        if len(categorias) > 0:
            translation = translate_client.translate([categoria.name for categoria in categorias],source_language='en',target_language='es')
            for i in range(0,len(translation)):
                categorias[i].name_es = translation[i]['translatedText']
                categorias[i].save()

    if debug and not partial:
        print("Tiempo de traduccion de objetos {}".format(time.time()-t))
        t = time.time()

    ## Imagenes
    print("Descargando imagenes")
    ### Solicitando tareas
    main_image_url = r['img'][0]['sizes'][12]['url']
    images = [(urlparse(main_image_url).path.split('/')[-1],download_file.delay(main_image_url))]
    for j in range(1,len(r['img'])):
        url = r['img'][j]['sizes'][12]['url']
        images.append((urlparse(url).path.split('/')[-1],download_file.delay(url)))
    #### Esperamos a la finalizacion de tareas
    images = [(img[0],img[1].get()) for img in images]

    ###Imagenes adicionales
    imagenes = []
    #### Ahora, el resto de imagenes
    for j in range(0,len(images)):
        imagen = modelos.Imagen()
        with open(images[j][1],'rb') as file:
            image_file = File(file)
            imagen.photo.save(images[j][0],image_file)
        imagenes.append(imagen)

    if debug:
        print("Tiempo de descarga de imagenes {}".format(time.time()-t))
        t = time.time()

    ## Creacion de Objeto
    objeto = modelos.Objeto()

    ### Asignamos los campos
    objeto.author = autor
    objeto.name = r['main']['name']
    objeto.description = r['main']['description']
    objeto.external_id = referencia_externa

    ###Imagen principal
    main_image_name = images[0][1]
    try:
        with open(images[0][1],'rb') as file:
            main_image = File(file)
            objeto.main_image.save(main_image_name,main_image)
    except:
        raise ValueError("Error al descargar imagen principal")

    ### Asigamos categorias y tags
    for categoria in categorias:
        objeto.category.add(categoria)
    for tag in tags:
        objeto.tags.add(tag)

    objeto.save()

    #Traducimos el nombre
    if not partial:
        objeto.translate_es()

    #Linkeamos los ForeignKey antes creados al objeto creado
    for imagen in imagenes:
        imagen.object = objeto
        imagen.save()

    #Limpiamos las imagenes
    for img in images:
        os.remove(img[1])

    #Es un archivo parcial? O continuamos trabajando?
    if not partial:
        add_files_to_thingiverse_object(objeto,file_list = file_list)
    else:
        objeto.partial = True
        objeto.save()

def add_files_to_thingiverse_object(objeto, file_list = None, override = False, debug = True):
        http = PoolManager(retries=Retry(total=5, status_forcelist=[500]))
        #Recuperamos el id del objeto
        if objeto.external_id != None:
            if objeto.external_id.repository != 'thingiverse':
                raise ValueError("El repositorio no es Thingiverse")
            thingiid = objeto.external_id.external_id
        else:
            raise ValueError("El objeto no tiene referencia externa")
        ## Archvos STL
        print("Preparando archivos")
        rfiles = request_from_thingi('things/{}/files'.format(thingiid))
        files_available_id = [a['id'] for a in rfiles]
        if file_list == None:
            file_list = files_available_id
        elif type(file_list) == list:
            pass
        ### Nos pasaron una lista de archivos valida?
        for id in file_list:
            if id not in files_available_id:
                print("IDs disponibles:")
                print(files_available_id)
                raise ValueError("IDs de archivos invalida: "+id)
        ### Tenemos una lista valida, procedemos a descargar los archivos
        print('Descargando lista de archivos:')
        print(file_list)
        archivos_link = []
        for id in file_list:
            for thing_file in rfiles:
                if id == thing_file['id']:
                    name = thing_file['name']
                    if '.stl' in name.lower():
                        download_url = thing_file['download_url']
                        archivos_link.append((urlparse(download_url).path.split('/')[-1],download_file.delay(download_url+'?access_token='+ApiKey.get_api_key())))
        #Con los archivos solicitados, se los solicitamos a celery y agregamos a DB
        archivos = []
        for link in archivos_link:
            link = (link[0],link[1].get())
            with open(link[1],'rb') as file:
                archivo = modelos.ArchivoSTL()
                archivo.file.save(objeto.external_id.repository+'-'+str(objeto.external_id.external_id)+'.stl',File(file))
                archivos.append(archivo)
                os.remove(link[1])
        ### Tenemos los archivos descargados. Necesitamos completar su tiempo de imp, peso, dimensiones
        print("Ejecutando trabajos de sliceo")
        slicer_jobs_ids = {}
        slicer_jobs_ids_poly = {}
        for archivo in archivos:
            archivos_r = {'file': archivo.file.open(mode='rb')}
            rf = requests.post(settings.SLICER_API_ENDPOINT, files = archivos_r)
            archivos_r = {'file': archivo.file.open(mode='rb')}
            parametros = {'escala_inicial':'0.2','escala_final':'1.6','escala_paso':'0.2'}
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
            rf_p = requests.get(settings.SLICER_API_ENDPOINT+'tiempo_en_funcion_de_escala/status/{}/'.format(slicer_jobs_ids_poly[archivo])).json()
            poly_coef = json.loads(rf_p['poly'])
            polinomio = modelos.Polinomio()
            polinomio.a0 = poly_coef[3]
            polinomio.a1 = poly_coef[2]
            polinomio.a2 = poly_coef[1]
            polinomio.a3 = poly_coef[0]
            polinomio.save()
            #Establecemos los coeficientes y guardamos
            rf = requests.get(settings.SLICER_API_ENDPOINT+'status/{}/'.format(slicer_jobs_ids[archivo])).json()
            archivo.printing_time_default = rf['tiempo_estimado']
            archivo.size_x_default = rf['size_x']
            archivo.size_y_default = rf['size_y']
            archivo.size_z_default = rf['size_z']
            archivo.weight_default = rf['peso']
            archivo.time_as_a_function_of_scale = polinomio
            #Antes de guardar el archivo, hacemos un examen de sanidad sobre los resultados del sliceo
            if slicer_results_sanity_check(res_file=rf,res_poly=rf_p):
                archivo.save()
            else:
                print("El archivo {} fue removido".format(archivo.name))
                archivos.remove(archivo)

        for archivo in archivos:
            archivo.object = objeto
            archivo.save()

        modelo_ar = modelos.ModeloAR()
        modelo_ar.object = objeto
        modelo_ar.save()

        #Preparamos el modelo AR
        modelo_ar.create_sfb(generate=True)

        objeto.save()

        #Es posible que el objeto no tenga ningun archivo, en cuyo caso, lo borramos
        if len(archivos) == 0:
            objeto.delete()

def slicer_results_sanity_check(res_file,res_poly):
    #El polinomio fue correctamente ajustado?
    if len(json.loads(res_poly['escalas'])) < 6:
        return False
    #El archivo es muy pequeño?
    if res_file['size_x']*res_file['size_y']*res_file['size_z'] < 5**3:
        return False
    return True

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

def import_from_thingiverse_parser(base):
    '''
    A partir de un BufferedReader de un archivo de pickle, importa las things
    '''
    base = pickle.load(base)
    for thing in base:
        try:
            add_object_from_thingiverse(thing['thing_id'],file_list = thing['thing_files_id'])
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
