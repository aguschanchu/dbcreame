from django.contrib import admin
from .models import Autor, Categoria, Tag, ReferenciaExterna, Polinomio, Objeto, Usuario, ObjetoPersonalizado, Compra, Imagen, ArchivoSTL, ModeloAR, Color, SfbRotationTracker, DireccionDeEnvio
from django.utils.html import format_html_join, format_html
from .render.plot_poly import polyplot
import trimesh
import os

@admin.register(Autor)
class AutorAdmin(admin.ModelAdmin):
    list_display = ('name', 'username','contact_email')

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('name','name_es','hidden')
    search_fields = ('name',)

@admin.register(ArchivoSTL)
class ArchivoSTLAdmin(admin.ModelAdmin):
    list_display = ('printing_time_default', 'time_as_a_function_of_scale', 'size_x_default',
    'size_y_default', 'size_z_default', 'weight_default')
    search_fields = ('name', )

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name','name_es')

@admin.register(Polinomio)
class PolinomioAdmin(admin.ModelAdmin):
    list_display = ('a0','a1','a2','a3','a4','a5')
    readonly_fields = ('image',)
    actions = ['rebuild_images']

    def image(self,obj):
        return format_html('<img src='+obj.plot.url+' width="40%" height="40%"></img>')

    def rebuild_images(self, request, queryset):
        for o in queryset:
            if o.plot is not None and not os.path.exists(o.plot.path):
                polyplot(o)

    rebuild_images.short_description = "Rebuild images"

@admin.register(ReferenciaExterna)
class ReferenciaExternaAdmin(admin.ModelAdmin):
    list_display = ('external_id','repository')

class ArchivoSTLInline(admin.TabularInline):
    model = ArchivoSTL
    verbose_name = "Modelos STL"
    verbose_name_plural = verbose_name
    classes = ['collapse','extrapretty']

class ImagenInline(admin.TabularInline):
    model = Imagen
    verbose_name = "Imagenes"
    verbose_name_plural = verbose_name
    classes = ['collapse']

class ModelARInline(admin.StackedInline):
    model = ModeloAR
    verbose_name = "Modelo AR"
    verbose_name_plural = verbose_name
    fk = "object"
    list_display = ('name','combined_stl','sfb_file','sfb_file_rotated','human_flag')
    list_filter = ('human_flag',)
    readonly_fields = ('name','image','combined_stl')

    fieldsets = (
        (None, {
            'fields': (('combined_stl','human_flag'),'image')
        }),
        ('Archivos', {
            'classes': ('collapse',),
            'fields': ('sfb_file','sfb_file_rotated'),
        })
    )
    def name(self,obj):
        return obj.objeto.name

    def image(self,obj):
        return format_html('<img src='+obj.modeloarrender.image_render.url+' width="40%" height="40%"></img>')


@admin.register(Objeto)
class ObjetoAdmin(admin.ModelAdmin):
    list_display = ('name','author','external_id','total_printing_time_default','human_flag')
    raw_id_fields = ('author',)
    filter_horizontal = ('category','tags')
    readonly_fields = ['view_main_image','total_printing_time_default','popular_color','filter_passed']
    inlines = [ArchivoSTLInline,ImagenInline,ModelARInline]
    fieldsets = (
            (None, {
                'fields': (('name','name_es'),)
                }),
            (None, {
                'fields': ('view_main_image',('author','like_count','total_printing_time_default','discount','hidden','filter_passed'),('default_color','popular_color'))
                }),
            ('Descripcion', {
                'fields': ('description',),
                'classes': ('collapse',)
                }),
            ('Categorias y tags', {
                'fields': ('category','tags'),
                'classes': ('collapse',)
                }),
            ('Referencia externa', {
                'fields': ('external_id',),
                'classes': ('collapse',)
                })
        )

    def total_printing_time_default(self, obj):
        try:
            return round(sum([o.printing_time_default for o in ArchivoSTL.objects.filter(object=obj)])/60**2, 2)
        except:
            return 0

    def human_flag(self, obj):
        return obj.modeloar.human_flag

    def filter_passed(self, obj):
        if hasattr(obj.external_id, 'thingiverse_attributes'):
            return obj.external_id.thingiverse_attributes.filter_passed
        else:
            return None

    human_flag.boolean = True
    filter_passed.boolean = True


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('user',)

@admin.register(SfbRotationTracker)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('object','rotated','usuario')

@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ('name','color','available')
    read_only = ('color')

    def color(self,obj):
        return format_html("<div style='background: #{}; height: 20px;'></div>".format(obj.code))


@admin.register(ObjetoPersonalizado)
class ObjetoPersonalizadoAdmin(admin.ModelAdmin):
    list_display = ('object_id','color','scale','quantity')

@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ('date','status','buyer')
    ordering = ('date',)

@admin.register(DireccionDeEnvio)
class CompraAdmin(admin.ModelAdmin):
    list_display = ('short_address','usuario','notes')

@admin.register(Imagen)
class ImagenAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    readonly_fields = ['view_image']
