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
from django.contrib.auth.models import User

class TestOperations(APITransactionTestCase):
    allow_database_queries = True

    def setUp(self):
        from populate import thingiverse_apikeys_setup, superuser_setup, mercadopago_setup, colors_setup
        superuser_setup(User)
        thingiverse_apikeys_setup(ApiKey)
        colors_setup(Color, settings)
        #Importamos un objeto para comprar
        objeto = ObjetoThingi.objects.create_object(external_id=1278865, origin='human')
        while objeto.status != 'SUCCESS':
            objeto.update_status()
            time.sleep(1)
        self.assertTrue(Objeto.objects.count() > 0)
        #Creamos el user que realizara las operaciones
        u = User.objects.create(username='test',password='test123', email='test_user_88801944@testuser.com')
        self.client.force_authenticate(user=u)

    def test_MP_purchase(self):
        #Preparamos el usuario de prueba de MP. Para su funcionamiento, ver https://github.com/mercadopago/sdk-php/issues/75
        acc = MPModels.Account()
        acc.app_id = '6591554033016558'
        acc.secret_key = 'I8PYPLOeZKIOroUzXznn7vfUIdpKkaW5'
        acc.sandbox = True
        acc.save()
        url = reverse('db:place_order')
        data = {'purchased_objects': [{'object_id' : Objeto.objects.first().id,'color': Color.objects.first().id, 'scale': 1, 'quantity': 1}],
                #Es la direccion de casa
                'delivery_address':
                    {'gmaps_id': 'ChIJP2unpHu1vJUR4HQAhsGujOQ',
                    'notes': 'Notas muy importantes'
                    },
                'buyer':
                    {'first_name': 'tuvi'}

                }
        response = self.client.post(url, data, format='json').json()
        id = response['id']
        #Creo la preferencia?
        self.assertTrue(MPModels.Preference.objects.count() > 0)
        return True
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

    def test_like_object(self):
        obj = Objeto.objects.first()
        url = reverse('db:like_object', kwargs={'id': obj.id})
        response = self.client.put(url, format='json').json()
        #Actualizamos el objeto
        obj = Objeto.objects.first()
        self.assertTrue(obj.like_count == 1)

    def test_object_comments(self):
        obj = Objeto.objects.first()
        url = reverse('db:create_comment')
        data = {'object': obj.id, 'comment': 'Este es un comentario muy relevante'}
        response = self.client.post(url, data, format='json').json()
        #Actualizamos el objeto
        obj = Objeto.objects.first()
        self.assertTrue(len(obj.comments) == 1)
        #Ahora buscamos ese mismo comentario, con el endpoint pertinente
        url = reverse('db:view_single_comment', kwargs={'id': obj.id})
        response = self.client.get(url).json()
        self.assertTrue(len(response) > 1)

    def test_review(self):
        obj = Objeto.objects.first()
        #Antes de postear una review, veamos que no hay problema con el puntaje inicial
        url = reverse('db:search_object_by_id', kwargs={'id': obj.id})
        response = self.client.get(url).json()
        self.assertTrue(response['points'] > 1)
        url = reverse('db:create_review')
        data = {'object': obj.id, 'points': 5}
        response = self.client.post(url, data, format='json').json()
        #Buscamos el objeto por ID, y veamos nuestra solida review
        url = reverse('db:search_object_by_id', kwargs={'id': obj.id})
        response = self.client.get(url).json()
        self.assertTrue(response['points'] == 5)





