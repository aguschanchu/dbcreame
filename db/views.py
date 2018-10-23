from db.serializers import ObjetoSerializer, TagSerializer, CategoriaSerializer, CompraSerializer, PaymentPreferencesSerializer, PaymentNotificationSerializer, ColorSerializer, SfbRotationTrackerSerializer, UsuarioSerializer, UserSerializer, AppSetupInformationSerializer
from db.models import Objeto, Tag, Categoria, Compra, Color, ObjetoPersonalizado, SfbRotationTracker, Usuario
from rest_framework import generics, status, pagination, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny
from django.http import Http404
from django.db.models import Q
from db.tools import price_calculator
import json
import traceback
from django_mercadopago import models as MPModels
import mercadopago
from . import tasks
# Auth
from django.contrib.auth.models import User
from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from django.conf import settings

# TEMP
import requests
'''
Pagination classes
'''
class ObjectPagination(pagination.CursorPagination):
    page_size = 10
    ordering = 'creation_date'

'''
Query views
'''

class CategoryView(generics.ListAPIView):
    serializer_class = ObjetoSerializer
    pagination_class = ObjectPagination
    lookup_url_kwarg = 'category'

    def get_queryset(self):
        category = self.kwargs.get(self.lookup_url_kwarg)
        objetos = Objeto.objects.filter(category__name=category,origin='human')
        return objetos

class TagView(generics.ListAPIView):
    #Devuelve todos los objetos que contengan a todos los tags (dados por un string separados por ,)
    serializer_class = ObjetoSerializer
    pagination_class = ObjectPagination
    lookup_url_kwarg = 'tags'

    def get_queryset(self):
        tags = self.kwargs.get(self.lookup_url_kwarg).split(',')
        objetos = Objeto.objects.all()
        for tag in tags:
            objetos = objetos.filter(tags__name=tag) | objetos.filter(tags__name_es=tag)
        return objetos

class ObjectView(generics.RetrieveAPIView):
    serializer_class = ObjetoSerializer
    lookup_url_kwarg = 'id'

    def get_object(self):
        id = self.kwargs.get(self.lookup_url_kwarg)
        objeto = Objeto.objects.get(id=id)
        return objeto

class NameView(generics.ListAPIView):
    serializer_class = ObjetoSerializer
    pagination_class = ObjectPagination
    lookup_url_kwarg = 'name'

    def get_queryset(self):
        name = self.kwargs.get(self.lookup_url_kwarg)
        objetos = Objeto.objects.filter(name__contains=name) | Objeto.objects.filter(name_es__contains=name)
        return objetos

class SearchView(generics.ListAPIView):
    '''
    Es el metodo de busqueda mas generico, y que mas resultados devuelve. Dado una lista de palabras separadas con
    espacio (strig), busca todos los objetos que contengan alguna de las palabras, sea en su nombre,
    o en alguna de sus tags
    '''
    serializer_class = ObjetoSerializer
    pagination_class = ObjectPagination
    lookup_url_kwarg = 'query'

    def get_queryset(self):
        query = self.kwargs.get(self.lookup_url_kwarg).split(' ')
        return Objeto.search_objects(query)


'''
List views
'''

class ListAllObjectsView(generics.ListAPIView):
    serializer_class = ObjetoSerializer
    pagination_class = ObjectPagination
    def get_queryset(self):
        return Objeto.objects.all()

class ListAllCategoriesView(generics.ListAPIView):
    serializer_class = CategoriaSerializer

    def get_queryset(self):
        return Categoria.objects.all()

class ListAllTagsView(generics.ListAPIView):
    serializer_class = TagSerializer
    def get_queryset(self):
        return Tag.objects.all()

class ListAllColorsView(generics.ListAPIView):
    serializer_class = ColorSerializer
    queryset = Color.objects.all()


'''
Orders views
'''

class ListAllOrdersView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = CompraSerializer

    def get_queryset(self):
        user = self.request.user
        return Compra.objects.filter(Q(buyer=user.usuario) & ~Q(status='checkout-pending'))

class GetPreferenceInfoFromMP(APIView):
    def post(self, request, mpid, format=None):
        mp_account = MPModels.Account.objects.first()
        mp_client = mercadopago.MP(mp_account.app_id, mp_account.secret_key)
        return Response(mp_client.get_preference(mpid)['response'])

class CreateOrderView(generics.CreateAPIView):
    serializer_class = CompraSerializer
    permission_classes = (IsAuthenticated,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        #Creamos la compra a partir de los datos serializados
        compra = serializer.save()
        #Asignamos el comprador
        user = request.user
        compra.buyer = user.usuario
        #Creamos la preferencia de pago de MP
        precio_total = price_calculator.get_order_price(compra)
        mp_account = MPModels.Account.objects.first()
        compra.payment_preferences = MPModels.Preference.objects.create(
            title='Compra del {}'.format(compra.date),
            price=precio_total,
            description='Compra en Creame3D',
            reference=str(compra.id),
            account=mp_account)
        #MP requiere email y nombre del comprador, de modo, que ingresamos esos datos
        mp_client = mercadopago.MP(mp_account.app_id, mp_account.secret_key)
        preference = {'payer': {'email': user.email if user.email != '' else 'compras@creame3d.com','name':user.username}}
        preferenceResult = mp_client.update_preference(compra.payment_preferences.mp_id, preference)
        #Devolvemos el resultado
        compra.save()
        serializer = self.get_serializer(compra)
        print('asd')
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data)

class CheckoutSuccessNotification(generics.RetrieveAPIView):
    serializer_class = CompraSerializer
    permission_classes = (IsAuthenticated,)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        #Cambiamos el estado de la instancia
        instance.status = 'pending-payment'
        instance.save()
        #Ejecutamos la comprobacion de pago
        tasks.query_mp_for_payment_status.delay(instance.id)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

'''
Operations views
'''

class ObjectView(generics.RetrieveAPIView):
    serializer_class = ObjetoSerializer
    lookup_url_kwarg = 'id'

    def get_object(self):
        id = self.kwargs.get(self.lookup_url_kwarg)
        try:
            objeto = Objeto.objects.get(id=id)
        except Objeto.DoesNotExist:
             raise Http404
        return objeto

class ToggleLike(generics.UpdateAPIView):
    permission_classes = (IsAuthenticated,)
    lookup_url_kwarg = 'id'

    def get_object(self):
        id = self.kwargs.get(self.lookup_url_kwarg)
        try:
            objeto = Objeto.objects.get(id=id)
        except Objeto.DoesNotExist:
             raise Http404
        return objeto

    def update(self, request, *args, **kwargs):
        objeto = self.get_object()
        id = self.kwargs.get(self.lookup_url_kwarg)
        user = request.user
        if user.usuario.liked_objects.filter(pk=id).exists():
            user.usuario.liked_objects.remove(objeto)
        else:
            user.usuario.liked_objects.add(objeto)
        serializer = ObjetoSerializer(objeto,context={'request': request})
        print(serializer)
        return Response(serializer.data)

class ToggleRotated(generics.CreateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = SfbRotationTrackerSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        #Existe ya la instancia en la DB? De ser así, actualizamos
        if SfbRotationTracker.objects.filter(object=serializer.validated_data['object'],usuario=request.user.usuario.id).exists():
            obj = SfbRotationTracker.objects.get(object=serializer.validated_data['object'],usuario=request.user.usuario.id)
            obj.rotated = serializer.validated_data['rotated']
            obj.save()
        else:
            SfbRotationTracker.objects.create(object=serializer.validated_data['object'],usuario=request.user.usuario,rotated=serializer.validated_data['rotated'])
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

class UserInformationView(generics.RetrieveUpdateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = UsuarioSerializer
    def get_object(self):
        return Usuario.objects.get(pk=self.request.user.usuario.id)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)

'''
DB Operations view
'''

class SendAppSetupInformation(APIView):
    def get(self, request, format=None):
        serializer = AppSetupInformationSerializer(price_calculator.obtener_parametros_de_precios())
        return Response(serializer.data)


'''
Social login views
'''

class FacebookLogin(SocialLoginView):
    adapter_class = FacebookOAuth2Adapter


class GoogleLogin(SocialLoginView):
    """Google OAuth login endpoint

    POST parameter `code` should contain the access code provided by Google OAuth backend,
    which the backend uses in turn to fetch user data from the Google authentication backend.

    POST parameter `access' might not function with this function.

    Requires `callback_url` to be properly set in the configuration, this is of format:

        callback_url = https://{domain}/accounts/google/login/callback/
    """

    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client
    callback_url = settings.CURRENT_PROTOCOL+ '://' + settings.CURRENT_HOST + ':' + str(settings.CURRENT_PORT) + '/db/accounts/google/login/callback/'

'''
Mercadopago
'''

class MercadopagoSuccessUrl(generics.RetrieveAPIView):
    serializer_class = PaymentNotificationSerializer
    lookup_url_kwarg = 'pk'

    def get_object(self):
        pk = self.kwargs.get(self.lookup_url_kwarg)
        try:
            preference = MPModels.Notification.objects.get(id=pk)
        except MPModels.Notification.DoesNotExist:
             raise Http404
        return preference
