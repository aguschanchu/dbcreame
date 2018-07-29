from db.serializers import ObjetoSerializer
from .models import Objeto
from rest_framework import generics
from rest_framework.permissions import IsAdminUser

class CategoryView(generics.ListAPIView):
    serializer_class = ObjetoSerializer
    lookup_url_kwarg = 'category'

    def get_queryset(self):
        category = self.kwargs.get(self.lookup_url_kwarg)
        objetos = Objeto.objects.filter(category__name=category)
        return objetos

class ObjectView(generics.RetrieveAPIView):
    serializer_class = ObjetoSerializer
    lookup_url_kwarg = 'id'

    def get_queryset(self):
        id = self.kwargs.get(self.lookup_url_kwarg)
        objeto = Objeto.objects.get(id=id)
        return objeto
