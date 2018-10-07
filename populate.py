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

def colors_setup(Color):
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

def testing_objects_setup():
    #Object population (for testing)
    valid_input = False
    while not valid_input:
        print("\nImporto objetos de ejemplo? (slicerapi debe estar prendido)")
        ans = input("Por favor, responde Y o N: ")
        if ans == "Y":
            valid_input = True
            print("Importando objetos....")
            add_object_from_thingiverse(1278865)
            add_object_from_thingiverse(1179160)
            add_object_from_thingiverse(2836304)
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
    from db.models import *
    from django.core.files import File
    from thingiverse.import_from_thingi import *
    import os, subprocess
    print('Populating Database...')
    print('----------------------\n')
    superuser_setup(User)
    mercadopago_setup(MPAccount)
    social_accounts_config(Site,SocialApp)
    thingiverse_apikeys_setup(ApiKey)
    colors_setup(Color)
    testing_objects_setup()
