from django.contrib import admin
from .models import Autor, Categoria, Tag, ReferenciaExterna, Polinomio, Objeto, Usuario, ObjetoPersonalizado, Compra, Album, ArchivoSTL

@admin.register(Autor)
class AutorAdmin(admin.ModelAdmin):
    list_display = ('name', 'username','contact_email')

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(ArchivoSTL)
class ArchivoSTLAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

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
    raw_id_fields = ('author',)
    filter_horizontal = ('category','tags','files')

@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('username',)

@admin.register(ObjetoPersonalizado)
class ObjetoPersonalizadoAdmin(admin.ModelAdmin):
    list_display = ('objeto','color','scale')

@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ('date','status')

@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    readonly_fields = ['imagen_principal']
