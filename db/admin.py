from django.contrib import admin
from .models import Autor, Categoria, Tag, ReferenciaExterna, Polinomio, Objeto, Usuario, ObjetoPersonalizado, Compra, Imagen, ArchivoSTL, ModeloAR
from django.utils.html import format_html_join, format_html
import trimesh

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
    list_display = ('name','author','external_id','total_printing_time_default')
    raw_id_fields = ('author','ar_model')
    filter_horizontal = ('category','tags','files')
    readonly_fields = ['view_main_image','total_printing_time_default']

    def total_printing_time_default(self,obj):
        return int(sum([o.printing_time_default for o in obj.files.all()])/60**2)


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('user',)

@admin.register(ModeloAR)
class ModelARAdmin(admin.ModelAdmin):
    list_display = ('name','combined_stl','sfb_file','human_flag')
    list_filter = ('human_flag',)
    readonly_fields = ('file_list', 'name','image')

    fieldsets = (
        (None, {
            'fields': (('combined_stl','human_flag'),)
        }),
        ('Lista de archivos', {
            'classes': ('extrapretty',),
            'fields': (('file_list','image'),)
        }),
        ('Modelos AR', {
            'classes': ('collapse',),
            'fields': ('sfb_file',),
        })
    )
    def name(self,obj):
        return obj.objeto.name

    def file_list(self,obj):
        return format_html_join(
        '\n', "<li><a href={}> {}</a></li>",
        ((o.file.url, o.name()) for o in obj.objeto.files.all())
        )

    def image(self,obj):
        return format_html('<img src='+obj.modeloarrender.image_render.url+' width="50%" height="50%"></img>')




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
