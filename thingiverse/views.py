from thingiverse.models import ApiKey
from thingiverse.serializers import ThingiverseAPIKeyRequestSerializer, ObjetoThingiSerializer
from thingiverse import import_from_thingi
from rest_framework import generics, status, pagination, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny
import traceback

class ThingiverseAPIKeyRequestView(APIView):
    permission_classes = (IsAdminUser,)

    def post(self, request, format=None):
        serializer = ThingiverseAPIKeyRequestSerializer(data=request.data)
        if serializer.is_valid():
            if not 'uses' in serializer.validated_data.keys():
                serializer.validated_data['uses'] = 1
            serializer.validated_data['api_key'] = ApiKey.get_api_key(serializer.validated_data['uses'])
            return Response(serializer.data)
        return Response(serializer.errors)

class AddObjectFromThingiverse(APIView):
    permission_classes = (IsAdminUser,)
    #Agregar objeto desde id y lista de archivos
    def post(self, request, format=None):
        serializer = ObjetoThingiSerializer(data=request.data)
        if serializer.is_valid():
            obj = serializer.save()
            #Ejecutamos la importacion
            try:
                job = import_from_thingi.add_object_from_thingiverse(obj.external_id,file_list=serializer.validated_data['file_list'],partial=False)
                obj.status = 'finished'
            except:
                traceback.print_exc()
                obj.status = 'error'
            obj.save()
            return Response(ObjetoThingiSerializer(obj).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors)
