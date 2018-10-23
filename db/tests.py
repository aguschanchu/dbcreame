from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITransactionTestCase
from db.models import *
from django.conf import settings
from thingiverse.models import *
from django.contrib.auth.models import User
from allauth.socialaccount.models import Site, SocialApp
from django_mercadopago import models as MPModels
from django.core.files import File
import os, subprocess, time


class TestPurchase(APITransactionTestCase):
    allow_database_queries = True

    def setUp(self):
        from populate import thingiverse_apikeys_setup, superuser_setup, mercadopago_setup, colors_setup
        superuser_setup(User)
        thingiverse_apikeys_setup(ApiKey)
        colors_setup(Color, settings)
        #Preparamos el usuario de prueba de MP. Para su funcionamiento, ver https://github.com/mercadopago/sdk-php/issues/75
        acc = MPModels.Account()
        acc.app_id = '6591554033016558'
        acc.secret_key = 'I8PYPLOeZKIOroUzXznn7vfUIdpKkaW5'
        acc.sandbox = True
        acc.save()
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
        data = {'purchased_objects': [{'object_id' : Objeto.objects.first().id,'color': Color.objects.first().id, 'scale': 1, 'quantity': 1}],
                #Es la direccion de casa
                'delivery_address':
                    {'gmaps_id': 'ChIJP2unpHu1vJUR4HQAhsGujOQ',
                    'notes': 'Notas muy importantes'
                    }
                }
        response = self.client.post(url, data, format='json').json()
        id = response['id']
        #Creo la preferencia?
        self.assertTrue(MPModels.Preference.objects.count() > 0)
        #TODO: Automatizar lo siguiente con selenium
        #Vamos a pedirle al user que pague la preferencia
        print("Necesito que pagues la preferencia de pago. Usa estas credenciales:")
        print("Usuario: test_user_88801944@testuser.com")
        print("Password: qatest9204")
        #No, no es la mia. Es de pruebas de MP.
        print("Tarjeta: 4509953566233704")
        print("URL: {}".format(response['payment_preferences']['payment_url']))
        valid_input = False
        while not valid_input:
            ans = input("Pagaste la preferencia? responde Y o N: ")
            if ans == "Y":
                valid_input = True
            elif ans == "N":
                return True
        #Notificamos que la preferencia termino exitosamente
        url = reverse('db:checkout_successful', kwargs={'id':id})
        compra = Compra.objects.get(pk=id)
        self.assertTrue(compra.payment_preferences.paid)
