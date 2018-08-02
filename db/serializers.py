from rest_framework import serializers
from .models import Objeto, ObjetoThingi, ArchivoSTL, Imagen, Autor, ReferenciaExterna, Polinomio

class PolinomioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Polinomio
        fields = ('a0','a1','a2','a3','a4','a5')

class ArchivoSTLSerializer(serializers.ModelSerializer):
    time_as_a_function_of_scale = PolinomioSerializer(read_only=True)
    class Meta:
        model = ArchivoSTL
        fields = ('id', 'file','printing_time_default','time_as_a_function_of_scale',
        'size_x_default', 'size_y_default', 'size_z_default', 'weight_default')

class ImagenSerializer(serializers.ModelSerializer):
    photo = serializers.ImageField(max_length=None, use_url=True, allow_null=True, required=False)
    class Meta:
        model = Imagen
        fields = ('photo', )

class AutorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Autor
        fields = ('id', 'name', 'username')

class ReferenciaExternaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferenciaExterna
        fields = ('repository', 'external_id')


class ObjetoSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField(many=True)
    tags = serializers.StringRelatedField(many=True)
    files = ArchivoSTLSerializer(many=True, read_only=True)
    images = ImagenSerializer(many=True, read_only=True)
    author = AutorSerializer(read_only=True)
    external_id = ReferenciaExternaSerializer(read_only=True)
    #images = serializers.StringRelatedField(many=True)
    #images = serializers.SlugRelatedField(many=True, read_only=True,slug_field='name')
    class Meta:
        model = Objeto
        fields = ('id', 'name', 'description', 'like_count', 'main_image', 'images',
         'files', 'author', 'creation_date', 'category', 'tags', 'external_id',
         'hidden')


class ObjetoThingiSerializer(serializers.ModelSerializer):
    class Meta:
        model = ObjetoThingi
        fields = ('id', 'external_id', 'status', 'file_list')
