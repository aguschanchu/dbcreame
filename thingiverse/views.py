from thingiverse.models import ApiKey, ObjetoThingi
from thingiverse.serializers import ThingiverseAPIKeyRequestSerializer, ObjetoThingiSerializer
from thingiverse import import_from_thingi
from rest_framework import generics, status, pagination, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny
import traceback
from .tasks import add_object_from_thingiverse_chain

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

class AddObjectFromThingiverse(generics.CreateAPIView):
    #permission_classes = (IsAdminUser,)
    serializer_class = ObjetoThingiSerializer

class AddObjectFromThingiverseStatus(generics.RetrieveAPIView):
    serializer_class = ObjetoThingiSerializer
    lookup_url_kwarg = 'pk'

    def get_object(self):
        pk = self.kwargs.get(self.lookup_url_kwarg)
        try:
            objeto = ObjetoThingi.objects.get(id=pk)
            objeto.update_status()
        except ObjetoThingi.DoesNotExist:
             raise Http404
        return objeto
