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
import os, subprocess


class ObjetoTest(APITransactionTestCase):
    allow_database_queries = True

    def setUp(self):
        from populate import thingiverse_apikeys_setup, superuser_setup
        superuser_setup(User)
        thingiverse_apikeys_setup(ApiKey)

    def test_import_from_thingi(self):
        self.assertTrue(ApiKey.objects.count() > 0)
        url = reverse('thingiverse:import_from_thingi_url')
        #Esta vista requiere estar logueado con admin
        user = User.objects.first()
        self.client.force_authenticate(user=user)
        data = {'external_id': '763622', 'file_list' : [1223854],'partial': True}
        cuenta_de_objetos = Objeto.objects.count()
        #Enviamos la request
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Objeto.objects.count(), cuenta_de_objetos+1)
