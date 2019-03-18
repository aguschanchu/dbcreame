from __future__ import absolute_import
from celery import shared_task, chord, group
import io
from vision import models as modelos
from google.cloud import vision as gvision
from google.cloud.vision import types
from thingiverse.tasks import request_from_thingi
from django.conf import settings
from db.models import Objeto
from thingiverse.models import ObjetoThingi
from urllib3.exceptions import MaxRetryError


'''
A partir de una imagen, ejecuta las tareas de importacion para los resultados de busqueda
'''
@shared_task(queue='vision', bind=True, max_retries=50, retry_backoff=True)
def process_image(self, id):
    objeto = modelos.ImagenVisionAPI.objects.get(pk=id)
    client = gvision.ImageAnnotatorClient()
    image_path = settings.BASE_DIR + objeto.image.url

    #Ejecutamos el reconocimiento de tags
    with io.open(image_path, 'rb') as image_file:
        content = image_file.read()
    image = types.Image(content=content)
    response = client.label_detection(image=image)
    #Guardamos resultados de busqueda
    for tag in response.label_annotations:
        modelos.TagSearchResult.objects.create(tag=tag.description,score=tag.score,parent=objeto)
    '''
    response.label_annotations tiene una lista de labels, donde cada uno, tiene un nombre
    y puntaje [0,1]. La idea, es:
    Para cada label (ordenados por score)
    1) Buscar objetos objetos en la db
    2) Busca en Thingiverse usando el search endpoint, y agrega VISION_RESULTS_AMOUNT a la db
    3) Aplicar el filtro a los resultados anteriores
    Si tiene al menos VISION_RESULTS_AMOUNT devulelve el resultado. Si no, vuelve al primer paso.
    '''
    label_list = sorted([a for a in response.label_annotations], key=lambda x: -x.score)

    for label in label_list:
        tag = label.description

        #Busqueda local
        local_search_results = Objeto.search_objects(tag)
        for o in local_search_results:
            c = modelos.ImagenVisionApiResult.objects.create(search=objeto, object=o, label_score=label.score)
            print("Agregue este objeto de la db:" + o.name + label.description + str(label.score))
            c.update_score()

        #Buscamos el tag en Thingiverse
        things_restantes = lambda: 5*settings.VISION_RESULTS_AMOUNT - objeto.search_result.count()

        #No queremos buscar más de VISION_RESULTS_AMOUNT por tag, y, al menos, buscar 5
        search_amount = max(5, min(settings.VISION_RESULTS_AMOUNT, things_restantes()))
        if search_amount > 0:
            search = search_tag_in_thingiverse.delay(objeto.id, tag, search_amount, label.score)
            modelos.ThingiverseSearch.objects.create(parent=objeto,celery_id=search.id)

    return True


@shared_task(queue='vision', bind=True, max_retries=50, retry_backoff=True)
def search_tag_in_thingiverse(self, search_id, tag, search_amount, score):
    objeto = modelos.ImagenVisionAPI.objects.get(pk=search_id)
    r = request_from_thingi('search/{}'.format(tag))
    # De la lista de resultados, ejecutamos la importacion parcial
    label_count = 0
    while r and label_count <= search_amount:
        # Hubo resultados?
        try:
            id = r.pop(0)['id']
        except:
            break
        # Antes de agregarlo, no esta ya como resultado de busqueda y/o pendiente de importacion, no?
        busqueda_pendiente = any([id == c.object.id for c in objeto.search_result.all() if c.object != None] +
                                 [id == c.subtask.external_id for c in objeto.search_result.all() if c.subtask != None])
        # No es uno de los objetos que ya teniamos en la DB, no?
        busqueda_preexistente = Objeto.objects.filter(external_id__external_id=str(id)).first()
        if busqueda_pendiente:
            pass
        elif busqueda_preexistente:
            c = modelos.ImagenVisionApiResult.objects.create(search=objeto, object=busqueda_preexistente,
                                                             label_score=score)
            c.update_score()
        else:
            subtask = ObjetoThingi.objects.create_object(external_id=id, partial=True, origin='vision')
            modelos.ImagenVisionApiResult.objects.create(search=objeto, subtask=subtask, label_score=score)

        label_count += 1