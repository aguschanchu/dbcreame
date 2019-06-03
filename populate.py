import os

def superuser_setup(User):
    #Superuser config
    username = 'agus'
    email = 'agusc@agusc.com.ar'
    password = 'Ferraro'

    u = User.objects.create_superuser(username, email, password)

def mercadopago_setup(MPAccount):
    #Mercadopago config
    acc = MPAccount()
    acc.name = "Creame3DMP"
    acc.slug = "C3DMP"
    if settings.CURRENT_HOST == "agusc.ovh":
        acc.secret_key = "***REMOVED***"
        acc.app_id = "***REMOVED***"
    elif settings.CURRENT_HOST == "api.creame3d.com":
        acc.secret_key = "***REMOVED***"
        acc.app_id = "***REMOVED***"
    else:
        print("ERROR: No se encontraron configuraciones de MP para este dominio")
        acc.secret_key = "***REMOVED***"
        acc.app_id = "***REMOVED***"
    acc.sandbox = True
    acc.save()
    print("Mecadopago added")

def social_accounts_config(Site,SocialApp):
    #Social accounts config
    ##Site onfig
    Site.objects.all()[0].delete()
    site = Site.objects.get_or_create(domain=settings.CURRENT_HOST,name=settings.CURRENT_HOST,id=1)[0]
    ##Google Config
    o = SocialApp()
    o.provider = "google"
    o.name = "Google Login - FirebaseNoname"
    o.client_id = "***REMOVED***"
    o.secret = "***REMOVED***"
    o.save()
    o.sites.add(site)
    o.save()
    ##Facebook Config
    o = SocialApp()
    o.provider = "facebook"
    o.name = "Facebook Login"
    o.client_id = "***REMOVED***"
    o.secret = "***REMOVED***"
    o.save()
    o.sites.add(site)
    o.save()
    print("Social accounts created")

def thingiverse_apikeys_setup(ApiKey):
    #ApiKeys (Thingiverse) population
    ***REMOVED***
    ***REMOVED***
    ***REMOVED***
    ***REMOVED***
    ***REMOVED***
    ***REMOVED***
    ***REMOVED***
    ***REMOVED***
    ***REMOVED***
    ***REMOVED***

    print("API Keys (Thingiverse) added")

def populate_categories(request_from_thingi,settings,CategoriaThigi):
    print("Populando categorias")
    #Categorias base en Thingiverse. No deberian cambiar
    base_categories = request_from_thingi('categories')
    for bcat in base_categories:
        category_info = request_from_thingi(bcat['url'].split(settings.THINGIVERSE_API_ENDPOINT)[1])
        parent = CategoriaThigi.objects.create(name=category_info['name'])
        for child in category_info['children']:
            CategoriaThigi.objects.create(name=child['name'],parent=parent)

def colors_setup(Color, settings):
    global subprocess, File, os
    if __name__ != '__main__':
        import os, subprocess
        from django.core.files import File
    print("Initiating colors population...")
    #Color population
    color_list = [('Blanco','FFFFFF'),('Verde oscuro','013100'),('Verde claro','12B50C'),('Celeste','0A73B8'),('Amarillo','FFF208'),('Azul','0954F5'),('Naranja','FF8400'),('Rojo','793A00'),('Gris','606060'),('Negro','000000')]
    for name, code in color_list:
        color = Color.objects.create(name=name,code=code)
        #Convertimos el par obj, mtl a SFB
        args = [settings.BASE_DIR + '/lib/sceneform_sdk/linux/converter','-d','--mat',settings.BASE_DIR + '/lib/sceneform_sdk/default_materials/obj_material.sfm',
        '--outdir', settings.BASE_DIR + '/tmp/',settings.BASE_DIR + '/resources/colors_reference/' + code + '.obj']
        proc = subprocess.run(args,universal_newlines = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        #Se proceso correctamente?
        for line in proc.stdout.splitlines():
            if 'Wrote SFB to' in line:
                break
        else:
            print(proc)
            print("Error al exportar SFB para el color {}".format(name))
        #Devolvemos el path del sfb
        sfb_path = settings.BASE_DIR + '/tmp/' + code + '.sfb'
        with open(sfb_path,'rb') as f:
            color.sfb_color_reference.save(code + '.sfb',File(f))
        os.remove(sfb_path)
    print("Colors added")


def prusa_profiles_setup():
    global slaicer_models, requests, ContentFile
    # Content file creation
    cf = slaicer_models.ConfigurationFile.objects.create(name='Prusa-settings', version='0.4.5', vendor='Prusa', provider='https://raw.githubusercontent.com/prusa3d/Slic3r-settings/master/live/PrusaResearch/0.4.5.ini')
    r = requests.get('https://raw.githubusercontent.com/prusa3d/Slic3r-settings/master/live/PrusaResearch/0.4.5.ini')
    cf.file.save('prusa.ini', ContentFile(r.content))
    cf.import_available_profiles()
    printer_profiles = ['Original Prusa i3 MK3']
    material_profiles = ['Prusa PLA']
    print_profiles = ['0.15mm QUALITY MK3', '0.20mm QUALITY MK3', '0.10mm DETAIL MK3', '0.05mm ULTRADETAIL MK3']
    # Available profiles import
    for o in slaicer_models.AvailableProfile.objects.all():
        if o.config_name in printer_profiles or o.config_name in material_profiles or o.config_name in print_profiles:
            o.convert()
    # We link the profiles
    printer_imported_profile = slaicer_models.PrinterProfile.objects.filter(config_name='Original Prusa i3 MK3').first()
    for o in slaicer_models.PrintProfile.objects.all():
        if o.config_name in print_profiles:
            o.compatible_printers_condition.add(printer_imported_profile)
    # Cambiamos el tamaño de cama
    printer_imported_profile.bed_shape = [600, 600, 600]
    printer_imported_profile.save()
    # Quoting profile creation
    slaicer_models.SliceConfiguration.objects.create(printer=slaicer_models.PrinterProfile.objects.last(), material=slaicer_models.MaterialProfile.objects.last(), quoting_profile=True)
    print("Quoting profiles added")

def testing_objects_setup():
    #Object population (for testing)
    valid_input = False
    while not valid_input:
        print("\nImporto objetos de ejemplo? (slicerapi debe estar prendido)")
        ans = input("Por favor, responde Y o N: ")
        if ans == "Y":
            valid_input = True
            print("Importando objetos....")
            ObjetoThingi.objects.create_object(external_id=1278865)
            ObjetoThingi.objects.create_object(external_id=1179160)
            ObjetoThingi.objects.create_object(external_id=2803935)
            ObjetoThingi.objects.create_object(external_id=3450069)

        elif ans == "N":
            valid_input = True
    print("Objects added")

    print("Migration finished successfully")


if __name__ == '__main__':
    print('\n' + ('=' * 80) + '\n')
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                          'dbcreame.settings')
    django.setup()
    from django.contrib.auth.models import User
    from django.conf import settings
    from django.db import IntegrityError
    from allauth.socialaccount.models import Site, SocialApp
    from django_mercadopago.models import Account as MPAccount
    from thingiverse.models import *
    from thingiverse.tasks import request_from_thingi
    from db.models import *
    from django.core.files import File
    from django.core.files.base import ContentFile
    from thingiverse.import_from_thingi import *
    from slaicer import models as slaicer_models
    import requests
    import os
    import subprocess
    print('Populating Database...')
    print('----------------------\n')
    superuser_setup(User)
    mercadopago_setup(MPAccount)
    social_accounts_config(Site,SocialApp)
    thingiverse_apikeys_setup(ApiKey)
    populate_categories(request_from_thingi,settings,CategoriaThigi)
    colors_setup(Color, settings)
    prusa_profiles_setup()
    testing_objects_setup()
