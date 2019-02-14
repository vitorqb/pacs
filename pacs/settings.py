"""
Django settings for pacs project.

Generated by 'django-admin startproject' using Django 2.1.3.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""

import os
import logging
from dotenv import load_dotenv

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Loads a .env file, if any
load_dotenv(os.path.join(BASE_DIR, '.env'), verbose=True)

DEBUG = os.environ.get('PACS_DEBUG', None) is not None
SECRET_KEY = os.environ['PACS_SECRET_KEY']
ALLOWED_HOSTS = os.environ['PACS_ALLOWED_HOSTS'].split(',')
STATIC_ROOT = os.environ['PACS_STATIC_ROOT']

# The Token that allows admin to log in
ADMIN_TOKEN = os.environ['PACS_ADMIN_TOKEN']

# We allow all since we use a security token anyway
CORS_ORIGIN_ALLOW_ALL = True

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'django_filters',
    'corsheaders',

    'mptt',

    'currencies',
    'accounts',
    'movements',
    'pacs_auth',
]

if DEBUG:
    INSTALLED_APPS += ['django_extensions', 'debug_toolbar']

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    *(['debug_toolbar.middleware.DebugToolbarMiddleware'] if DEBUG else []),
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Mine
    'pacs_auth.middleware.PacsAuthMiddleware'
]

ROOT_URLCONF = 'pacs.urls'

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

WSGI_APPLICATION = 'pacs.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.environ['PACS_DB_FILE'],
        'TEST': {
            'NAME': os.path.join(BASE_DIR, 'test_db.sqlite3')
        }
    }
}


# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATIC_URL = '/static/'

# Logging
if DEBUG is False:
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'file': {
                'level': 'DEBUG',
                'class': 'logging.FileHandler',
                'filename': os.path.expanduser(os.environ['PACS_LOG_FILE'])
            },
        },
        'loggers': {
            '': {
                'handlers': ['file'],
                'level': 'DEBUG',
                'propagate': True,
            },
        },
    }


# Django rest
REST_FRAMEWORK = {
    'TEST_REQUEST_DEFAULT_FORMAT': 'json'  # Always use json on tests
}


INTERNAL_IPS = ['127.0.0.1']
