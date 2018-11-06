from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITransactionTestCase
from db.models import *
from django.contrib.auth.models import User
from django.conf import settings
from django.db import IntegrityError
from allauth.socialaccount.models import Site, SocialApp
from django_mercadopago.models import Account as MPAccount
from thingiverse.import_from_thingi import *
from thingiverse.tasks import request_from_thingi
from thingiverse.models import *
from django.core.files import File
import time
import os, subprocess


class ObjetoTest(APITransactionTestCase):
    allow_database_queries = True

    def setUp(self):
        from populate import thingiverse_apikeys_setup, superuser_setup, populate_categories
        superuser_setup(User)
        thingiverse_apikeys_setup(ApiKey)
        populate_categories(request_from_thingi,settings,CategoriaThigi)
        #Fueron importadas correctamente las API Keys?
        self.assertTrue(ApiKey.objects.count() > 0)
        print(ApiKey.objects.count())

    def test_vision_expierence(self):
        url = reverse('vision:post_url')
        #Preparamos imagen a postear
        with open(settings.BASE_DIR + '/static/tests/elephant.jpeg','rb') as file:
            image = File(file)
            data = {'image' : image}
            #Enviamos la request
            response = self.client.post(url, data, format='multipart')
        #Recibimos el id, y esperamos a que se termine de agregar a la db
        id = response.json()['id']
        for _ in range(0,600):
            response = self.client.get(reverse('vision:status_url', kwargs={'id':id})).json()['status']
            if response == "SUCCESS":
                break
            time.sleep(0.1)
        #Veamos los resultados
        response = self.client.get(reverse('vision:retrieve_url', kwargs={'id':id})).json()['results']
        #Obtuvo resultados?
        self.assertTrue(len(response) > 5)
        #Perfecto. Elegimos alguno, y pedimos que cargue todos los items!
        objeto = Objeto.objects.get(pk=response[0]['id'])
        print(objeto)
        #Deberia ser un objeto parcial, importado en el test anterior
        self.assertEqual(objeto.partial, True)
        cantidad_inicial_de_archivos = len(objeto.files.all())
        #Pedimos ahora que complete a la thing
        url = reverse('thingiverse:import_from_thingi_url')
        data = {'object_id': objeto.id, 'update_object': True}
        response = self.client.post(url, data, format='json')
        id = response.json()['id']
        url = reverse('thingiverse:import_from_thingi_url_status', kwargs={'pk':id})
        for _ in range(0,6000):
            response = self.client.get(url).json()['status']
            if response == "SUCCESS":
                break
            time.sleep(1)
        self.assertTrue(len(objeto.files.all())>cantidad_inicial_de_archivos)
