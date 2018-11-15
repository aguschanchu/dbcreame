# Register your models here.
from django.contrib import admin
from django.utils.html import format_html_join, format_html
from .models import ImagenVisionAPI

@admin.register(ImagenVisionAPI)
class ImagenVisionApiAdmin(admin.ModelAdmin):
    list_display = ('id', 'query_time')
    readonly_fields = ('image',)

    def image(self,obj):
        return format_html('<img src='+obj.image.url+' width="40%" height="40%"></img>')