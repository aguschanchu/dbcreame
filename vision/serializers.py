from rest_framework import serializers
from vision.models import ImagenVisionAPI, TagSearchResult

class TagSearchResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = TagSearchResult
        fields = ('tag','score')

class ImagenVisionAPISerializer(serializers.ModelSerializer):
    tag_search_result = TagSearchResultSerializer(many=True)
    class Meta:
        model = ImagenVisionAPI
        fields = ('id','image','status','search_results','tag_search_result')
        read_only_fields=('status','search_results','tag_search_result')

    def create(self, validated_data):
        return ImagenVisionAPI.objects.create_object(**validated_data)
