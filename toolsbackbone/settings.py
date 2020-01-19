# pylint: disable=wrong-import-order
"""
Django settings for toolsbackbone project.

Generated by 'django-admin startproject' using Django 2.2.6.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""
import django_heroku

import os
from distutils.util import strtobool


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '!8(y8(55&m6i*yp_8z4do-c7$bbpg+=02)d5k6_-87m&1wzzgf'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = bool(strtobool(os.environ.get('DJANGO_DEBUG', 'false')))

ALLOWED_HOSTS = []

SECURE_SSL_REDIRECT = bool(
    strtobool(os.environ.get('DJANGO_HTTPS_ONLY', 'true')))


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'rest_auth',
    'graphene_django',
    'api',
    'trader'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 'api.middleware.TokenAuthMiddleware',
]

ROOT_URLCONF = 'toolsbackbone.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'toolsbackbone.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': 'localhost',
        'PORT': int(os.environ.get('DJANGO_DB_PORT', 5432)),
        'NAME': os.environ.get('DJANGO_DB_NAME', None),
        'USER': os.environ.get('DJANGO_DB_USER', None),
        'PASSWORD': os.environ.get('DJANGO_DB_PASS', None)
    }
}


# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

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

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'


# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# teart naive datetime warnings as errors during development
if DEBUG:
    import warnings
    warnings.filterwarnings(
        'error', r"DateTimeField .* received a naive datetime",
        RuntimeWarning, r'django\.db\.models\.fields',
    )


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

STATIC_URL = '/static/'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': ('%(asctime)s [%(process)d] [%(levelname)s] ' +
                       'pathname=%(pathname)s lineno=%(lineno)s ' +
                       'funcname=%(funcName)s %(message)s'),
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'simple': {
            'format': '[%(levelname)s] %(message)s'
        }
    },
    'handlers': {
        'heroku': {
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['heroku'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
        },
        'django.db': {
            'handlers': ['heroku'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO') if bool(
                strtobool(os.getenv('DJANGO_LOG_DB', 'false'))) else 'INFO',
            'propagate': False,
        },
        'trader': {
            'handlers': ['heroku'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
        },
        # 'trader.api': {
        #     'handlers': ['console'],
        #     'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
        #     'formatter': 'verbose',
        #     'propagate': True,
        # },
        # 'trader.providers': {
        #     'handlers': ['console'],
        #     'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
        #     'formatter': 'verbose',
        #     'propagate': True,
        # },
        # 'trader.aio.providers': {
        #     'handlers': ['console'],
        #     'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
        #     'formatter': 'verbose',
        #     'propagate': True,
        # },
        # 'trader.autopilot': {
        #     'handlers': ['console'],
        #     'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
        #     'formatter': 'verbose',
        #     'propagate': True,
        # }
    },
}

# ---------------------------------------------------------
#
# Third Party Settings
#
# ---------------------------------------------------------


# ---------------------------
# rest framework
# ---------------------------

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ]
}


# ---------------------------
# django-rest-auth
# ---------------------------

ACCOUNT_LOGOUT_ON_GET = True


# ---------------------------
# Graphene Settings
# ---------------------------

GRAPHENE = {
    'SCHEMA': 'api.graphql.schema.schema'
}


# ---------------------------
# Misc. Settings
# ---------------------------

AUTOPILOT_CAPACITY = int(os.getenv('DJANGO_AUTOPILOT_CAPACITY', '5'))

# ---------------------------
# Heroku settings
# ---------------------------

# This should always be the last line
django_heroku.settings(locals(), logging=not bool(
    strtobool(os.getenv('DJANGO_LOGGING', 'false'))))
