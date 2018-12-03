"""
Django settings for dbcreame project.

Generated by 'django-admin startproject' using Django 2.0.7.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.0/ref/settings/
"""

import os
from .localenv import *

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '***REMOVED***'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['api.creame3d.com','localhost','127.0.0.1','192.168.1.2','agusc.ovh','192.168.100.104']

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    #Autenticacion django-rest-auth
    'rest_framework',
    'rest_framework.authtoken',
    'rest_auth',
    'rest_auth.registration',
    #Autenticacion con allauth (via social auth)
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.facebook',
    'allauth.socialaccount.providers.google',
    #Procesamiento de imagenes
    'imagekit',
    #Mercadochorros
    'django_mercadopago',
    #Testeo lindo
    'django_nose',
    #Celery
    'django_celery_results',
    #Aplicaciones propias
    'db',
    'thingiverse',
    'vision',
    'photogrammetry',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'request_logging.middleware.LoggingMiddleware',
]

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['console'],
            'level': 'DEBUG',  # change debug level as appropiate
            'propagate': False,
        },
    },
}


ROOT_URLCONF = 'dbcreame.urls'

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',
            ],
        },
    },
]

WSGI_APPLICATION = 'dbcreame.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'dbapi',
        'USER': 'dbapi',
        'PASSWORD': '***REMOVED***',
        'HOST': '127.0.0.1',
        'PORT': '',
        'OPTIONS': {
           'sslmode': 'disable',
        }
    }
}


# Password validation
# https://docs.djangoproject.com/en/2.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/2.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

ADMIN_SITE_HEADER = "NoName DB Administration"

SITE_ID = 1

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',
    )
    }

AUTHENTICATION_BACKENDS = (
       # Needed to login by username in Django admin, regardless of `allauth`
    'django.contrib.auth.backends.ModelBackend',

    # `allauth` specific authentication methods, such as login by e-mail
    'allauth.account.auth_backends.AuthenticationBackend',
)




# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.0/howto/static-files/

STATIC_URL = '/static/'
MEDIA_ROOT = 'media/'
MEDIA_URL = '/media/'
FILE_UPLOAD_PERMISSIONS = 0o644
DATA_UPLOAD_MAX_MEMORY_SIZE = 25*1024**2
FILE_UPLOAD_MAX_MEMORY_SIZE = 25*1024**2

#Allauth configuration
SOCIALACCOUNT_EMAIL_VERIFICATION = None
SOCIALACCOUNT_EMAIL_REQUIRED = False
SOCIALACCOUNT_QUERY_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = None

#MercadoLibre configuration
MERCADOPAGO = {
    'autoprocess': True,
    'success_url': 'db:success_url',
    'failure_url': 'myapp:mp_failure',
    'pending_url': 'myapp:mp_pending',
    'base_host': CURRENT_PROTOCOL + '://' + CURRENT_HOST
}
#Significa que todos los pagos son tomados como validos
MERCADOPAGO_SANDBOX_MODE = True

#Celery config
CELERY_RESULT_BACKEND = 'django-db'
CELERY_BROKER_URL = 'amqp://'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_SOFT_TIME_LIMIT = 600*3
CELERY_CHORD_UNLOCK_MAX_RETRIES = 60
CELERY_PREFETCH_MULTIPLIER = 1
CELERY_QUEUES = ('http','celery','low_priority')

#Configuraciones adicionales
SLICER_API_ENDPOINT = 'http://api.creame3d.com:7000/slicer/'
THINGIVERSE_API_ENDPOINT = 'https://api.thingiverse.com/'
DB_ADMIN_USERNAME = 'agus'
DB_ADMIN_PASSWORD = 'Ferraro'

#Configuracion de APIs de Google (Translate y Vision)
GOOGLE_APPLICATION_CREDENTIALS = "google_credentials.json"
GOOGLE_MAPS_API_KEY = "***REMOVED***"

#Configuracion de Vision
VISION_RESULTS_AMOUNT = 10

#Configuraciones de precios
PRECIO_POR_HORA_DE_IMPRESION = 40
