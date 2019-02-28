# -*- coding: utf-8 -*-
import http.cookiejar
import tempfile
import urllib.request, urllib.parse, urllib.error
import urllib.parse
import pickle
import logging
import os
import time

import requests
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
COOKIE_PATH = os.path.join(BASE_DIR, "cookie.txt")
CACHE_PATH = os.path.join(BASE_DIR, "/cache")
REQUEST_WAIT = 8


def get_task_from_externtal_server(server, task_path, cookie=None, task_uuid=None):
    url = urllib.parse.urljoin(server, str(task_path))
    logger.debug("url: " + url)
    response = requests.get(url=url, cookies=cookie, verify=False)

    if response.status_code != 200:
        message = "Could not download task from " + str(url) + "The task does not exist: " + str(response.status_code)
        raise IOError(message)
    else:
        try:
            with tempfile.NamedTemporaryFile(delete=False) as task_file:
                task_file.write(response.content)
        except Exception:
            raise Exception("Error while saving task in tempfile")
    return task_file


def answer_format_template(award, message, format=None, awarded=None):
    if format is None or "loncapaV1":
        return """<loncapagrade>
        <awarddetail>%s</awarddetail>
        <message><![CDATA[%s]]></message>
        <awarded></awarded>
        </loncapagrade>""" % (award, message)
    else:
        return """<loncapagrade>
        <awarddetail>%s</awarddetail>
        <message><![CDATA[%s]]></message>
        <awarded>%s</awarded>
        </loncapagrade>""" % (award, message, awarded)

