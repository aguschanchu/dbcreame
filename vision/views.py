from django.shortcuts import render
from rest_framework import generics, status, pagination, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny
from vision.serializers import ImagenVisionAPISerializer
from vision.models import ImagenVisionAPI
from db.views import ObjectPagination
from db.serializers import ObjetoSerializer
'''
VisionAPI Views
'''

class VisionAPIPostURL(generics.CreateAPIView):
    serializer_class = ImagenVisionAPISerializer

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

class VisionAPIViewURL(generics.ListAPIView):
    serializer_class = ObjetoSerializer
    pagination_class = ObjectPagination
    lookup_url_kwarg = 'id'

    def get_queryset(self):
        id = self.kwargs.get(self.lookup_url_kwarg)
        #Buscamos la tarea por id
        job = ImagenVisionAPI.objects.get(pk=id)
        job.update_status()
        return job.search_results.all()
