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
@shared_task(bind=True,autoretry_for=(MaxRetryError,))
def process_image(self,id):
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
    1) Para cada label, buscar objetos objetos en la db
    2) Si no se tiene al menos VISION_RESULTS_AMOUNT objetos, busca en Thingiverse
    usando el search endpoint
    3) Aplicar el filtro a los resultados anteriores
    '''
    tag_list = [a.description for a in response.label_annotations]
    local_search_results = Objeto.search_objects(tag_list)
    for o in local_search_results:
        objeto.search_results.add(o)
    #Basta con los resultados locales? Devolvemos eso
    if len(objeto.search_results.all()) > settings.VISION_RESULTS_AMOUNT:
        return True
    #No basta? Buscamos en Thingiverse las distintas tags
    things_ids_a_agregar = set()
    things_restantes = lambda: settings.VISION_RESULTS_AMOUNT - len(objeto.search_results.all()) - len(things_ids_a_agregar)
    while tag_list and 0 <= things_restantes():
        tag = tag_list.pop(0)
        r = request_from_thingi('search/{}'.format(tag))
        #De la lista de resultados, ejecutamos la importacion parcial
        while r and 0 <= things_restantes():
            id = r.pop(0)['id']
            #No es uno de los objetos que ya teniamos en la DB, no?
            busqueda_preexistente = Objeto.objects.filter(external_id__external_id=str(id)).first()
            if busqueda_preexistente:
                objeto.search_results.add(busqueda_preexistente)
            else:
                things_ids_a_agregar.add(id)
    #Con la lista de cosas a agregar, ejecutamos la importacion.
    for id in things_ids_a_agregar:
        o = ObjetoThingi.objects.create_object(external_id=id,partial=True,origin='vision')
        objeto.subtasks.add(o)
    return True

'''    return ImageLabel.from_entity_annotation_list(response.label_annotations)
    def from_entity_annotation_list(annotation_list) -> List['ImageLabel']:
        label_list = []
        for annotation in annotation_list:
            label_list.append(
                ImageLabel(annotation.mid,
                           annotation.description,
                           annotation.score,
                           annotation.topicality)
            )

        return label_list
'''
