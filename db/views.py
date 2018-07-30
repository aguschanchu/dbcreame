from db.serializers import ObjetoSerializer
from .models import Objeto, Album
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.http import Http404
import json

class CategoryView(generics.ListAPIView):
    serializer_class = ObjetoSerializer
    lookup_url_kwarg = 'category'

    def get_queryset(self):
        category = self.kwargs.get(self.lookup_url_kwarg)
        objetos = Objeto.objects.select_related('image').filter(category__name=category)
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
        image = []
        for a in [getattr(objeto.image, a) for a in dir(Album) if 'pic' in a]:
            try:
                image.append(a.url)
            except ValueError:
                pass
        respuesta['image'] = json.dumps(image)
        return Response(respuesta)
