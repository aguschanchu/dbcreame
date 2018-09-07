import os

def populate():

    print('Populating Database...')
    print('----------------------\n')

    #Superuser config
    username = 'agus'
    email = 'agusc@agusc.com.ar'
    password = 'Ferraro'
    create_super_user(username, email, password)

    #Mercadopago config
    acc = MPAccount()
    acc.name = "Creame3DMP"
    acc.slug = "C3DMP"
    if settings.CURRENT_HOST == "agusc.ovh"
        acc.secret_key = "***REMOVED***"
        acc.app_id = "***REMOVED***"
    elif settings.CURRENT_HOST == "api.creame3d.com"
        acc.secret_key = "***REMOVED***"
        acc.app_id = "***REMOVED***"
    else:
        print("ERROR: No se encontraron configuraciones de MP para este dominio")
    acc.sandbox = True
    acc.save()
    print("Mecadopago added")

    #Social accounts config
    site = Site.objects.get_or_create(domain=settings.CURRENT_HOST,name=settings.CURRENT_HOST)[0]
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

    #ApiKeys (Thingiverse) population
    ***REMOVED***
    ***REMOVED***
    ***REMOVED***
    ***REMOVED***
    print("API Keys (Thingiverse) added")

    #Color population
    color_list = [('Verde oscuro','013100'),('Verde claro','12B50C'),('Amarillo','FFF208'),('Azul','0954F5'),('Celeste','0A73B8'),('Naranja','FF8400'),('Rojo','793A00'),('Gris','606060'),('Negro','000000'),('Blanco','FFFFFF')]
    for name, code in color_list:
        Color.objects.create(name=name,code=code)
    print("Colors added")

    print("Migration finished successfully")

def create_super_user(username, email, password):
    try:
        u = User.objects.create_superuser(username, email, password)
        return u
    except IntegrityError:
        pass



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
    from db.tools.import_from_thingi import *
    from db.models import *
    populate()
