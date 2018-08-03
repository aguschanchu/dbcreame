from db.serializers import ObjetoSerializer, ObjetoThingiSerializer, TagSerializer
from .models import Objeto, ObjetoThingi
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.http import Http404
from .tools import import_from_thingi
import json
import traceback

class CategoryView(generics.ListAPIView):
    serializer_class = ObjetoSerializer
    lookup_url_kwarg = 'category'

    def get_queryset(self):
        category = self.kwargs.get(self.lookup_url_kwarg)
        objetos = Objeto.objects.filter(category__name=category)
        return objetos

class TagView(generics.ListAPIView):
    serializer_class = ObjetoSerializer
    lookup_url_kwarg = 'tags'

    def get_queryset(self):
        tags = self.kwargs.get(self.lookup_url_kwarg).split(',')
        objetos = Objeto.objects.all()
        for tag in tags:
            objetos = objetos.filter(tags__name=tag)
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
    lookup_url_kwarg = 'name'

    def get_queryset(self):
        name = self.kwargs.get(self.lookup_url_kwarg)
        objetos = Objeto.objects.filter(name__contains=name)
        return objetos

class AddObjectFromThingiverse(APIView):
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
