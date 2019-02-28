# -*- coding: utf-8 -*-
"""
Django settings for proforma project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '5kde@@d5!sf012te$aoay9s6%jot5(ud4^#iqwszljp*ae1c$5'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = ["*", ]


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'taskget',
    'api',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'request_logging.middleware.LoggingMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    #'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'urls'

#WSGI_APPLICATION = 'proforma.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
#     }
# }

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'de-de'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

#STATIC_ROOT = '/var/www/proforma/static/'
STATIC_URL = '/static/'

try:
    from .settings_local import *
except ImportError:
    pass

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(message)s %(request)r'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'debug.log'),
            'formatter': 'verbose'
        },
        'error-file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'error.log'),
            'formatter': 'verbose'
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True,
        },
    },
    'loggers': {
        'api': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',  # change debug level as appropiate
            'propagate': False,
        },
        'taskget': {
            'handlers': ['console', 'file'],
            'level': 'INFO',  # change debug level as appropiate
            'propagate': False,
            'maxBytes': 1024*1024*4,  # 15MB
            'backupCount': 10,  # keep 10 historical versions
        },
        'django': {
            'handlers': ['console', 'error-file', 'file'],
            'level': 'DEBUG',  # change debug level as appropiate
            'propagate': False,
            'maxBytes': 1024*1024*4,  # 15MB
            'backupCount': 10,  # keep 10 historical versions
        },
        'django.request': {
            'handlers': ['console', 'error-file', 'file'],
            'level': 'INFO',  # change debug level as appropiate
            'propagate': False,
            'maxBytes': 1024*1024*4,  # 15MB
            'backupCount': 10,  # keep 10 historical versions
        }

    }
}