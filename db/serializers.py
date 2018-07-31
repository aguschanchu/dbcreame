from rest_framework import serializers
from .models import Objeto


class ObjetoSerializer(serializers.ModelSerializer):

     main_image = serializers.ReadOnlyField(source='image.pic0.url')
     class Meta:
        model = Objeto
        fields = ('id', 'name', 'description', 'like_count', 'files',
        'image', 'main_image', 'author', 'creation_date', 'category', 'tags', 'printing_time_default',
        'time_as_a_function_of_scale', 'size_x_default', 'size_y_default', 'size_z_default',
        'weight_default')
