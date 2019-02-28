# -*- coding: utf-8 -*-
import tempfile
from urllib.parse import urlparse

from django.core.serializers import json
from django.http import HttpResponse
from django.utils.datastructures import MultiValueDictKeyError
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

import os
import re
import urllib
import requests
import shutil
import logging
import xmlschema
import pprint
from requests.exceptions import InvalidSchema

from taskget.views import get_task_from_externtal_server, answer_format_template

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
PARENT_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CACHE_PATH = os.path.join(BASE_DIR, "/cache")
logger = logging.getLogger(__name__)


def grade_api_v2(request,):
    """
    grade_api_v2
    rtype: grade_api_v2
    """
    xml_version = None
    lms_is_lon_capa = False
    answer_format = "proformav2"
    xml_dict = dict()
    post_content = ""

    # debugging uploaded files
    for field_name, file in request.FILES.items():
        filename = file.name
        logger.debug("request.Files: " + str(file) + "\tfilename: " + str(filename))

    try:
        if check_lon_capa(request):
            lms_is_lon_capa = True
            answer_format = "loncapaV1"
    except Exception as e:
        logger.exception("check_lon_capa\r\n" +str(type(e))+str(e.args))
        return response_error("Error while check_lon_capa")

    # check POST returns submission_xml or raise exception with msg
    try:
        xml = check_post(request)
    except KeyError as e:
        return response_error(msg="No submisson attached", format=answer_format)
    except Exception as e:
        logger.exception("check_post\r\n" + str(type(e))+str(e.args))
        return response_error(msg="Error while check_post", format=answer_format)

    # get xml version
    try:
        xml_version = get_xml_version(submission_xml=xml)
    except Exception as e:
        logger.exception("get_xml_version\r\n" + str(type(e)) + str(e.args))
        return response_error(msg="get_xml_version", format=answer_format)

    try:
        if xml_version:
            logger.debug("xml: " + str(xml))
            is_valid = validate_xml(xml=xml, xml_version=xml_version)
        else:
            logger.debug("no version - " + str(xml))
            is_valid = validate_xml(xml=xml)
    except Exception as e:
        logger.debug(str(type(e))+str(e.args))
        return response_error(msg="validate_xml error: " + str(e.args), format=answer_format)

    if is_valid is False:
        logger.debug("validate_xml failed")
        return response_error(msg="no valid answer submitted -> check xsd", format=answer_format)

    try:
        submission_dict = xml2dict(xml)
    except Exception as e:
        logger.exception(str(type(e))+str(e.args))
        return response_error(msg="xml2dict", format=answer_format)

    try:
        task_type_dict = check_task_type(submission_dict)
    except Exception as e:
        logger.exception(str(type(e))+str(e.args))
        return response_error(msg="xml2dict", format=answer_format)

    if task_type_dict.get("external-task"):
        external_task_http_field = False
        task_file = None
        task_uri = task_type_dict["external-task"].get("task_path")  # todo check uri
        task_uuid = task_type_dict["external-task"].get("task_uuid")
        logger.debug("task_uri: " + str(task_uri))
        ##

        # test file-field
        m = re.match(r"(http\-file\:)(?P<file_name>.+)", task_uri)
        file_name = None
        if m:
            file_name = m.group('file_name')

        if file_name is not None:
            external_task_http_field = True
            logger.debug("file_name: " + str(file_name))
            try:
                for filename, file in request.FILES.items():
                    name = request.FILES[filename].name
                    if name == file_name:
                        task_filename = name
                        task_file = file
                if task_file is None:
                    return response_error(msg="task is not attached - Request-Files", format=answer_format)
            except Exception:
                raise Exception("Error while reading task")
        else:
            logger.debug("file_name is None ")
            try:
                # getTask todo: check cache for uuid
                parse_uri = urlparse(task_uri)
                # scheme://netloc/path;parameters?query#fragment

                parse_path = parse_uri.path + "?" + parse_uri.query
                logger.debug("parse_path: " + parse_path)
                task_file = get_task_from_externtal_server(server=parse_uri.scheme + "://" + parse_uri.netloc,
                                                           task_path=parse_path)
            except InvalidSchema as e:
                logger.exception(str(type(e))+str(e.args))
                return response_error(msg="external url is not valid", format=answer_format)
            except Exception as e:
                logger.exception(str(type(e))+str(e.args))
                return response_error(msg="login + get task", format=answer_format)
    try:
        submission_type = check_submission_type(submission_dict, request)
    except Exception as e:
        logger.exception(str(type(e))+str(e.args))
        return response_error(msg="check_submission_type", format=answer_format)
    # todo external submission
    if submission_type.get("embedded_files"):
        try:
            submission_zip_obj = file_dict2zip(submission_type.get("embedded_files"))
            submission_zip = {"submission" + ".zip": submission_zip_obj}  # todo name it to the user + course
        except Exception as e:
            logger.exception(str(type(e))+str(e.args))
            return response_error(msg="file_dict2zip", format=answer_format)

    elif submission_type.get("external-submission"):
        logger.debug("submission_type: external-submission")
        try:
            submission_zip_obj = file_dict2zip(submission_type.get("external-submission"))
            submission_zip = {"submission" + ".zip": submission_zip_obj}  # todo name it to the user + course
            logger.debug("external-submission" + str(submission_zip))
        except Exception as e:
            logger.exception(str(type(e))+str(e.args))
            return response_error(msg="file_dict2zip", format=answer_format)

    # create task and get Id
    try:
        if external_task_http_field is False:
            task_filename = os.path.basename(parse_uri.path)
        task_id = create_external_task(content_file_obj=task_file, server=settings.GRADERV, taskFilename=task_filename,
                                       formatVersion=answer_format)
    except Exception as e:
        logger.exception(str(type(e))+str(e.args))
        return response_error(msg="create_external_task", format=answer_format)

    # send submission to grader
    try:
        grade_result = send_submission2external_grader(request=request, server=settings.GRADERV, taskID=task_id,
                                                       files=submission_zip, answer_format=answer_format)
    except Exception as e:
        logger.exception(str(type(e))+str(e.args))
        return response_error(msg="send_submission2external_grader", format=answer_format)
    logger.debug("grade_result: " + grade_result)
    return HttpResponse(grade_result)


def check_post(request):
    """
    check the POST-Object
    1. could be just a submission.xml
    2. could be a submission.zip

    :rtype: submission.xml
    :param request: 
    """
    # todo check encoding of the xml -> first line
    encoding = 'utf-8'
    if not request.POST:
        if request.FILES:
                try:
                    # submission.xml in request.Files
                    logger.debug("FILES.keys(): " + str(request.FILES.keys()))
                    if request.FILES['submission.xml'].name is not None:
                        xml_dict = dict()
                        xml_dict[request.FILES['submission.xml'].name] = request.FILES['submission.xml']
                        logger.debug("xml_dict.keys(): " + str(xml_dict.keys()))
                        xml = xml_dict.popitem()[1].read()
                        xml_decoded = xml.decode(encoding)
                        return xml_decoded
                    elif request.FILES['submission.zip'].name:
                        # todo zip handling -> praktomat zip
                        raise Exception("zip handling is not implemented")
                    else:
                        raise KeyError("No submission attached")
                except MultiValueDictKeyError:
                    raise KeyError("No submission attached")
        else:
            raise KeyError("No submission attached")
    else:
        xml = request.POST.get("submission.xml")
        # logger.debug(request.POST)request.POST
        if xml is None:
            raise KeyError("No submission attached -> submission.xml")
        return xml


def check_lon_capa(request):
    """
    check if LMS is LON-CAPA
    :param request:
    :return:
    """
    if request.POST.get("LONCAPA_student_response"):
        return True
    else:
        return False


def answer_format(award, message, format=None, awarded=None):
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


def response_error(msg, format):
    """

    :param msg:
    :return: response
    """
    response_data = dict()
    response_data['message'] = msg
    return HttpResponse(status=500, content=json.dumps(response_data), content_type="application/json")


def get_xml_version(submission_xml):
    pass  # todo check namespace for version
    return "proforma_v2.0"


def validate_xml(xml, xml_version=None):
    logger.debug("xml_version: " + xml_version)
    if xml_version is None:
        logger.debug("PARENT_BASE_DIR: " + PARENT_BASE_DIR)
        schema = xmlschema.XMLSchema(os.path.join(PARENT_BASE_DIR, 'xsd/proforma_v2.0.xsd'))
        try:
            schema.validate(xml)
        except Exception as e:
            logger.error("Schema is not valid: " + str(e))
            raise Exception("Schema is not valid: " + str(e))
    else:
        if settings.PROFORMA_SCHEMA.get(xml_version):
            schema = xmlschema.XMLSchema(settings.PROFORMA_SCHEMA.get(xml_version))
            try:
                schema.validate(xml)
            except Exception as e:
                logger.error("Schema is not valid: " + str(e))
                raise Exception("Schema is not valid: " + str(e))
        else:
            logger.exception("validate_xml: schema ist not supported")
            raise Exception("schema ist not supported")

    return True


def xml2dict(xml):
    schema = xmlschema.XMLSchema(os.path.join(PARENT_BASE_DIR, 'xsd/proforma_v2.0.xsd'))  # todo fix this
    xml_dict = xmlschema.to_dict(xml_document=xml, schema=schema)
    return xml_dict


def check_task_type(submission_dict):
    if submission_dict.get("external-task"):
        task_path = submission_dict["external-task"]["$"]
        task_uuid = submission_dict["external-task"]["@uuid"]
        return {"external-task": {"task_path": task_path, "task_uuid": task_uuid}}
    elif submission_dict.get("task"):
        return "task"
    elif submission_dict.get("inline-task-zip"):
        return "inline-task-zip"
    else:
        return None


def check_submission_type(submission_dict, request):
    if submission_dict.get("external-submission"):
        submission_files_dict = None
        field_name = submission_dict["external-submission"]
        if field_name is not None:
            m = re.match(r"(http\-file\:)(?P<file_name>.+)", field_name)
            file_name = None
            if m:
                file_name = m.group('file_name')

        if file_name is not None:
            logger.debug("submission file_name: " + str(file_name))
            try:
                for filename, file in request.FILES.items():
                    name = request.FILES[filename].name
                    if name == file_name:
                        submission_files_dict = dict()
                        submission_files_dict.update({name: str(file.read(), encoding='utf-8', errors='replace')})
                        logger.debug(str(submission_files_dict))
                        break
                if submission_files_dict is None:
                    raise Exception("submission is not attached - Request-Files")
            except Exception as e:
                raise Exception("Error while reading task" + e)
        return{"external-submission": submission_files_dict}
    elif submission_dict.get("files"):
        # todo get a dict of files
        # embedded-files
        submission_files_dict = dict()
        if submission_dict["files"]["file"]:
            for sub_file in submission_dict["files"]["file"]:
                filename = sub_file["embedded-txt-file"]["@filename"]
                try:
                    file_content = sub_file["embedded-txt-file"]["$"]
                except KeyError:
                    raise Exception("No submission attached")
                submission_files_dict.update({filename: file_content})
            return {"embedded_files": submission_files_dict}
    else:
        raise Exception("No submission attached")


def file_dict2zip(file_dict):
    tmp_dir = tempfile.mkdtemp()

    try:

        os.chdir(os.path.dirname(tmp_dir))
        for key in file_dict:
            if os.path.dirname(key) == '':
                with open(os.path.join(tmp_dir, key), 'w') as f:
                    f.write(file_dict[key])
            else:
                if not os.path.exists(os.path.join(tmp_dir, os.path.dirname(key))):
                    os.makedirs(os.path.join(tmp_dir, os.path.dirname(key)))
                with open(os.path.join(tmp_dir, key), 'w') as f:
                    f.write(file_dict[key])

        submission_zip = shutil.make_archive(base_name="submission", format="zip", root_dir=tmp_dir)
        submission_zip_fileobj = open(submission_zip, 'rb')
        return submission_zip_fileobj
    except IOError as e:
        raise IOError("IOError:", "An error occurred while open zip-file", e)
    except Exception as e:
        raise Exception("zip-creation error:", "An error occurred while creating zip: E125001: "
                        "Couldn't determine absolute path of '.'", e)
    finally:
        shutil.rmtree(tmp_dir)


def create_external_task(content_file_obj, server, taskFilename, formatVersion):

    FILENAME = taskFilename

    try:
        files = {FILENAME: open(content_file_obj.name, 'rb')}
    except IOError:  #
        files = {FILENAME: content_file_obj}
    url = urllib.parse.urljoin(server, 'importTask')
    result = requests.post(url, files=files)

    if result.headers['Content-Type'] == 'application/json':
        logger.debug(result.text)
        try:
            taskid = result.json().get('taskid')
        except ValueError:
            message = "Error while creating task on grader: " + str(ValueError)
            raise ValueError(message)
        except Exception:
            message = "Error while creating task on grader: " + str(Exception)
            raise Exception(message)
        return taskid
    else:
        message = "Error while creating task on grader: unknown " + result.text
        raise IOError(message)


def send_submission2external_grader(request, server, taskID, files, answer_format):
    serverpath = urllib.parse.urlparse(server)
    domainOutput = "external_grade/" + str(answer_format) + "/v1/task/"
    path = "/".join([str(x).rstrip('/') for x in [serverpath.path, domainOutput, str(taskID)]])
    gradingURL = urllib.parse.urljoin(server, path)
    logger.debug("gradingURL: " + gradingURL)
    result = requests.post(url=gradingURL, files=files)
    if result.status_code == requests.codes.ok:
        return result.text
    else:
        logger.exception("send_submission2external_grader: " + str(result.status_code) + "result_text: " + result.text)
        raise Exception(result.text)