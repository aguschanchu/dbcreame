from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from db.models import *
from thingiverse.models import *
from django.contrib.auth.models import User
from django.conf import settings
from allauth.socialaccount.models import Site, SocialApp
from django_mercadopago.models import Account as MPAccount
from django.core.files import File
import os, subprocess


class TestPurchase(APITransactionTestCase):
    allow_database_queries = True

    def setUp(self):
        from populate import thingiverse_apikeys_setup, superuser_setup, mercadopago_setup, colors_setup
        superuser_setup(User)
        thingiverse_apikeys_setup(ApiKey)
        mercadopago_setup(MPAccount)
        colors_setup(Color)
        #Importamos un objeto para comprar
        objeto = ObjetoThingi.objects.create_object(external_id=1278865, origin='human')
        while objeto.status != 'SUCCESS':
            objeto.update_status()
            time.sleep(1)
        self.assertTrue(Objeto.objects.count() > 0)
        #Logueamos con el usuario admin
        user = User.objects.first()
        self.client.force_authenticate(user=user)

    def test_MP_purchase(self):
        url = reverse('db:place_order')
        data = {'purchased_objects': [{'object_id' : objeto.object_id,'color': Color.objects.first().id, 'scale': 1, 'quantity': 1}]}
