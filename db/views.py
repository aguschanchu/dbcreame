from db.serializers import ObjetoSerializer, ObjetoThingiSerializer, TagSerializer, CategoriaSerializer, UserSerializer, CompraSerializer, PaymentPreferencesSerializer, PaymentNotificationSerializer, ColorSerializer
from db.models import Objeto, Tag, Categoria, Compra, Color, ObjetoPersonalizado
from rest_framework import generics, status, pagination
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny
from django.http import Http404
from .tools import import_from_thingi, price_calculator
import json
import traceback
from django_mercadopago import models as MPModels
import mercadopago
# Auth
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
        objetos = Objeto.objects.filter(category__name=category)
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
        objetos_n = Objeto.objects.none()
        objetos_t = Objeto.objects.none()
        for word in query:
            objetos_n = objetos_n | Objeto.objects.filter(name__contains=word) | Objeto.objects.filter(name_es__contains=word)
        for word in query:
            objetos_t = objetos_t | Objeto.objects.filter(tags__name_es=word) | Objeto.objects.filter(tags__name=word)

        return (objetos_t | objetos_n).distinct()


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
        return Compra.objects.filter(buyer=user.usuario)

class GetPreferenceInfoFromMP(APIView):
    def get(self, request, mpid, format=None):
        mp_account = MPModels.Account.objects.first()
        mp_client = mercadopago.MP(mp_account.app_id, mp_account.secret_key)
        return Response(mp_client.get_preference(mpid))

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
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

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

'''
DB Operations view
'''

class AddObjectFromThingiverse(APIView):
    permission_classes = (IsAdminUser,)
    #Agregar objeto desde id y lista de archivos
    def post(self, request, format=None):
        serializer = ObjetoThingiSerializer(data=request.data)
        if serializer.is_valid():
            obj = serializer.save()
            #Ejecutamos la importacion
            try:
                job = import_from_thingi.add_object_from_thingiverse(obj.external_id,obj.file_list)
                obj.status = 'finished'
            except:
                traceback.print_exc()
                obj.status = 'error'
            obj.save()
            return Response(ObjetoThingiSerializer(obj).data)
        return Response(serializer.errors)

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
