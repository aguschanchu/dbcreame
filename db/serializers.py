from rest_framework import serializers
from .models import Objeto, ObjetoThingi, Categoria, Tag, Usuario, ObjetoPersonalizado, Compra, ArchivoSTL, Imagen, ModeloAR
from django.contrib.auth.models import User, AnonymousUser
from django_mercadopago import models as MPModels


class ArchivoSTLSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArchivoSTL
        depth = 4
        fields = ('id','file','printing_time_default','size_x_default','size_y_default','size_z_default','weight_default','time_as_a_function_of_scale')

class ImagenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Imagen
        fields = ('photo',)

class ModeloArSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModeloAR
        fields = ('combined_stl','human_flag','sfb_file')

class ObjetoSerializer(serializers.ModelSerializer):
    #images = serializers.StringRelatedField(many=True)
    #images = serializers.SlugRelatedField(many=True, read_only=True,slug_field='name')

    def liked_get(self,obj):
        print(self.context['request'].user)
        if self.context['request'].user.is_authenticated:
            return self.context['request'].user.usuario.liked_objects.filter(pk=obj.id).exists()
        else:
            return False
    liked = serializers.SerializerMethodField('liked_get')

    files = ArchivoSTLSerializer(many=True)
    images = ImagenSerializer(many=True)
    ar_model = ModeloArSerializer(source='modeloar')

    class Meta:
        depth = 4
        model = Objeto
        fields = ('id', 'name', 'name_es', 'description', 'like_count', 'main_image', 'images',
         'files', 'author', 'creation_date', 'category', 'tags', 'external_id', 'liked',
         'hidden','ar_model')

class ObjetoThingiSerializer(serializers.ModelSerializer):
    class Meta:
        model = ObjetoThingi
        fields = ('id', 'external_id', 'status', 'file_list')

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = '__all__'

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username',)


'''
Definimos el serializador de Compra con un poco mas de cuidado, para poder serializar
en forma nesteada una compra; simplificando la creacion de estas.
'''

class ObjetoPersonalizadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ObjetoPersonalizado
        fields = ('name','object_id','color','scale','quantity')

class PaymentPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = MPModels.Preference
        fields = '__all__'

class PaymentNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = MPModels.Notification
        fields = '__all__'

class CompraSerializer(serializers.ModelSerializer):
    purchased_objects = ObjetoPersonalizadoSerializer(many=True)
    payment_preferences = PaymentPreferencesSerializer()
    class Meta:
        model = Compra
        fields = ('id','buyer','purchased_objects','date','status','delivery_address','payment_preferences')
