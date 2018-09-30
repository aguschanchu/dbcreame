from db import models as modelos
from django.db import models
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
from .tasks import request_from_thingi, get_thing_categories_list, download_file

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
