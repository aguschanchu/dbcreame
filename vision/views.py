from django.shortcuts import render
from rest_framework import generics, status, pagination, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny
from vision.serializers import ImagenVisionAPISerializer, ImagenVisionApiResultSerializer
from vision.models import ImagenVisionAPI
from db.serializers import ObjetoSerializer
'''
VisionAPI Views
'''

class VisionAPIPostURL(generics.CreateAPIView):
    serializer_class = ImagenVisionAPISerializer

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

class VisionAPIStatusURL(generics.RetrieveAPIView):
    serializer_class = ImagenVisionAPISerializer
    lookup_url_kwarg = 'id'

    def get_object(self):
        id = self.kwargs.get(self.lookup_url_kwarg)
        #Buscamos la tarea por id
        job = ImagenVisionAPI.objects.get(pk=id)
        job.update_status()
        return job

'''
Pagination classes
'''
class VisionResultPagination(pagination.CursorPagination):
    page_size = 20
    ordering = '-score'

    def get_paginated_response(self, data):
        return Response({
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': [o['object'] for o in data]
        })

class VisionAPIViewURL(generics.ListAPIView):
    serializer_class = ImagenVisionApiResultSerializer
    pagination_class = VisionResultPagination
    lookup_url_kwarg = 'id'

    def get_queryset(self):
        id = self.kwargs.get(self.lookup_url_kwarg)
        #Buscamos la tarea por id
        job = ImagenVisionAPI.objects.get(pk=id)
        job.update_status()
        return job.search_results
