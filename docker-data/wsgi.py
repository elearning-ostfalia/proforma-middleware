"""
WSGI config for proforma project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
"""

import os
import sys
base_path = os.path.dirname(os.path.abspath(__file__))
# Add the app's directory to the PYTHONPATH
sys.path.append('/middleware/proforma')
sys.path.append('/middlware/proforma/proforma')

os.environ['DJANGO_SETTINGS_MODULE'] = 'proforma.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
