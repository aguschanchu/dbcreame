from django.contrib import admin
from .models import Autor, Categoria, Tag, ReferenciaExterna, Polinomio, Objeto, Usuario, ObjetoPersonalizado, Compra, Imagen, ArchivoSTL, ModeloAR

@admin.register(Autor)
class AutorAdmin(admin.ModelAdmin):
    list_display = ('name', 'username','contact_email')

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(ArchivoSTL)
class ArchivoSTLAdmin(admin.ModelAdmin):
    list_display = ('name', 'printing_time_default', 'time_as_a_function_of_scale', 'size_x_default',
    'size_y_default', 'size_z_default', 'weight_default')
    search_fields = ('name', )

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Polinomio)
class PolinomioAdmin(admin.ModelAdmin):
    list_display = ('a0','a1','a2','a3','a4','a5')

@admin.register(ReferenciaExterna)
class ReferenciaExternaAdmin(admin.ModelAdmin):
    list_display = ('external_id','repository')

@admin.register(Objeto)
class ObjetoAdmin(admin.ModelAdmin):
    list_display = ('name','author','external_id')
    raw_id_fields = ('author','ar_model')
    filter_horizontal = ('category','tags','files')
    readonly_fields = ['view_main_image']

@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('user',)

@admin.register(ModeloAR)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('combined_stl','sfb_file')

@admin.register(ObjetoPersonalizado)
class ObjetoPersonalizadoAdmin(admin.ModelAdmin):
    list_display = ('object_id','color','scale','quantity')

@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ('date','status')

@admin.register(Imagen)
class ImagenAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    readonly_fields = ['view_image']
