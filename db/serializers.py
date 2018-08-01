from rest_framework import serializers
from .models import Objeto, ObjetoThingi


class ObjetoSerializer(serializers.ModelSerializer):
     class Meta:
        model = Objeto
        fields = ('id', 'name', 'description', 'like_count', 'files',
        'images', 'main_image', 'author', 'creation_date', 'category', 'tags', 'printing_time_default',
        'time_as_a_function_of_scale', 'size_x_default', 'size_y_default', 'size_z_default',
        'weight_default')

class ObjetoThingiSerializer(serializers.ModelSerializer):
    class Meta:
        model = ObjetoThingi
        fields = ('id', 'external_id', 'status', 'file_list')
