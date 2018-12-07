from .settings import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'test_dbapi',
        'USER': 'dbapi',
        'PASSWORD': '***REMOVED***',
        'HOST': 'localhost',
        'PORT': '',
        'OPTIONS': {
           'sslmode': 'disable',
        }
    }
}
