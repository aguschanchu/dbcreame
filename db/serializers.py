from rest_framework import serializers
from .models import Objeto, ObjetoThingi, Categoria, Tag, Usuario
from django.contrib.auth.models import User


class ObjetoSerializer(serializers.ModelSerializer):
    #images = serializers.StringRelatedField(many=True)
    #images = serializers.SlugRelatedField(many=True, read_only=True,slug_field='name')

    def liked_get(self,obj):
        return self.context['request'].user.usuario.liked_objects.filter(pk=obj.id).exists()
    liked = serializers.SerializerMethodField('liked_get')

    class Meta:
        depth = 4
        model = Objeto
        fields = ('id', 'name', 'description', 'like_count', 'main_image', 'images',
         'files', 'author', 'creation_date', 'category', 'tags', 'external_id', 'liked',
         'hidden')

class ObjetoThingiSerializer(serializers.ModelSerializer):
    class Meta:
        model = ObjetoThingi
        fields = ('id', 'external_id', 'status', 'file_list')

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('name', )

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ('name', )

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username',)
