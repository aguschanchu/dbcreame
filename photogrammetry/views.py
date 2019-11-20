from django.shortcuts import render
from rest_framework import generics, status, pagination, serializers
from rest_framework.views import APIView
from .serializers import EscaneoSerializer, ImagenSerializer
from .models import Escaneo

class CreateJobView(generics.CreateAPIView):
    serializer_class = EscaneoSerializer

class AddImageToJob(generics.CreateAPIView):
    serializer_class = ImagenSerializer

class ViewJob(generics.RetrieveAPIView):
    serializer_class = EscaneoSerializer
    lookup_url_kwarg = 'id'

    def get_object(self):
        id = self.kwargs.get(self.lookup_url_kwarg)
        objeto = Escaneo.objects.get(id=id)
        return objeto

    def post(self, request, *args, **kwargs):
        print(request.data)
        return self.create(request, *args, **kwargs)