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
from thingiverse.models import *
from django.core.files import File
import time
import os, subprocess
from .filters.things_filter import *


class ObjetoTest(APITransactionTestCase):
    allow_database_queries = True

    def setUp(self):
        from populate import thingiverse_apikeys_setup, superuser_setup
        superuser_setup(User)
        thingiverse_apikeys_setup(ApiKey)
        #Fueron importadas correctamente las API Keys?
        self.assertTrue(ApiKey.objects.count() > 0)
        #Logueamos con el usuario admin
        user = User.objects.first()
        self.client.force_authenticate(user=user)
        #Preparamos las urls


    #Importacion parcial de objeto de Thingiverse
    def test_import_from_thingi_partial(self):
        t = time.time()
        url = reverse('thingiverse:import_from_thingi_url')
        data = {'external_id': '763622', 'file_list' : [1223854], 'partial': True, 'origin': 'human'}
        cuenta_de_objetos = Objeto.objects.count()
        #Enviamos la request
        response = self.client.post(url, data, format='json')
        #Recibimos el id, y esperamos a que se termine de agregar a la db
        id = response.json()['id']
        #Se termino de agregar?
        url = reverse('thingiverse:import_from_thingi_url_status', kwargs={'pk':id})
        print(url)
        for _ in range(0,600):
            response = self.client.get(url).json()['status']
            if response == "SUCCESS":
                break
            time.sleep(0.1)
        self.assertEqual(Objeto.objects.count(), cuenta_de_objetos+1)
        print("Tiempo de importacion parcial de objeto: {}s".format(time.time()-t))

    def test_add_objects_to_partial_thing(self):
        t = time.time()
        self.test_import_from_thingi_partial()
        objeto = Objeto.objects.all()[0]
        #Deberia ser un objeto parcial, importado en el test anterior
        self.assertEqual(objeto.partial, True)
        cantidad_inicial_de_archivos = len(objeto.files.all())
        #Mismo codigo que antes
        url = reverse('thingiverse:import_from_thingi_url')
        data = {'object_id': objeto.id, 'file_list' : [1223854,1475623], 'update_object': True}
        response = self.client.post(url, data, format='json')
        id = response.json()['id']
        url = reverse('thingiverse:import_from_thingi_url_status', kwargs={'pk':id})
        for _ in range(0,6000):
            response = self.client.get(url).json()['status']
            if response == "SUCCESS":
                break
            time.sleep(2)
        self.assertEqual(len(objeto.files.all()), cantidad_inicial_de_archivos+2)
        print("Tiempo de importacion total de objeto: {}s".format(time.time()-t))

    def test_objects_filter(self):
        o = ObjetoThingi.objects.create_object(external_id=3024248)
        while o.status != 'SUCCESS':
            o.update_status()
        obj = o.object_id
        #Veamos ahora los resultados del filtro
        self.assertTrue(obj.external_id.thingiverse_attributes.filter_passed)
        #Asimismo, deberiamos habernos quedado con unicamente 3 archivos
        self.assertTrue(len([o for o in obj.files.all() if o.informacionthingi.filter_passed == True]) == 3)

class CategoriaThingiTest(APITransactionTestCase):
    allow_database_queries = True

    def setUp(self):
        from populate import thingiverse_apikeys_setup
        thingiverse_apikeys_setup(ApiKey)

    def test_populate_categories(self):
        from populate import populate_categories
        populate_categories(request_from_thingi,settings,CategoriaThigi)
        self.assertTrue(CategoriaThigi.objects.count() > 2)
