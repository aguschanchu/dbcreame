from db.serializers import ObjetoSerializer, ObjetoThingiSerializer
from .models import Objeto, ObjetoThingi
from rest_framework import generics
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

class ObjectView(APIView):
    def get(self, request, id, format=None):
        try:
            objeto = Objeto.objects.get(pk=id)
        except:
            raise Http404
        serializer = ObjetoSerializer(objeto)
        respuesta = serializer.data
        #Reemplazamos las ids de categorias, imagenes, tags, y autores, por sus respectivos nombres
        respuesta['category'] = json.dumps([a.name for a in objeto.category.all()])
        respuesta['tags'] = json.dumps([a.name for a in objeto.tags.all()])
        respuesta['author'] = objeto.author.name
        respuesta['images'] = json.dumps([a.photo.url for a in objeto.images.all()])

        return Response(respuesta)

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
