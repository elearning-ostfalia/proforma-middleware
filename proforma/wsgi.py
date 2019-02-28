"""
WSGI config for rmsv2 project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/howto/deployment/wsgi/
"""

import os
import sys
import site
from django.core.wsgi import get_wsgi_application

# Add the site-packages of the chosen virtualenv to work with
site.addsitedir('/middleware/proforma/venv/lib/python3.4/site-packages')

# Add the app's directory to the PYTHONPATH
sys.path.append('/middleware/proforma')
sys.path.append('/middleware/proforma/proforma')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "proforma.settings")

# Activate your virtual env
activate_env=os.path.expanduser("/middleware/proforma/venv/bin/activate_this.py")
exec(open(activate_env).read(), dict(__file__=activate_env))

application = get_wsgi_application()
