from __future__ import absolute_import, unicode_literals
from celery import shared_task
from .models import ApiKey
from django.conf import settings
import json, random, string
import time
import urllib3
from urllib3.util import Retry
import requests
from urllib.parse import urlparse
from urllib3 import PoolManager

def get_api_key_from_db():
    #Nos logueamos con la cuenta de admin de la DB
    username = settings.DB_ADMIN_USERNAME
    password = settings.DB_ADMIN_PASSWORD
    url = settings.CURRENT_PROTOCOL+ '://' + settings.CURRENT_HOST + ':' + str(settings.CURRENT_PORT)
    r = requests.post(url+'/db/accounts/login/',data={'username': username, 'password': password}).json()
    if 'key' not in r.keys():
        raise ValueError('Error al loguear a la DB')
    #Solicitamos la APIKey
    r = requests.post(url+'/thingiverse/get_api_key/', data={'uses': 1}, headers = {'Authorization': 'Token '+ r['key']}).json()
    if 'api_key' not in r.keys():
        raise ValueError('Error al solicitar APIKey')
    return r['api_key']

@shared_task
def request_from_thingi(url,content=False,params='',k=None):
    endpoint = settings.THINGIVERSE_API_ENDPOINT
    http = PoolManager(retries=Retry(total=5, status_forcelist=[500]))
    for _ in range(0,60):
        if not k:
            k = get_api_key_from_db()
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
def get_thing_categories_list(thingiid,k=None):
    endpoint = settings.THINGIVERSE_API_ENDPOINT
    rcat = json.loads(request_from_thingi('things/{}/categories'.format(thingiid),k))
    print(rcat)
    print(type(rcat))
    result = []
    #Para cada una de las categorias, accedemos a la URL de esta
    for cat in rcat:
        category_info = json.loads(request_from_thingi(cat['url'].split(endpoint)[1],k))
        category_name = category_info['name']
        has_parent = 'parent' in category_info
        #Es una subcategoria? De ser así, accedemos a la padre
        while has_parent:
            category_info = json.loads(request_from_thingi(category_info['parent']['url'].split(endpoint)[1],k))
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
