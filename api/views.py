# -*- coding: utf-8 -*-
from taskget.views import answer_format_template, get_task_from_externtal_server
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils.datastructures import MultiValueDictKeyError
from api import api_v2
import urllib.parse
import requests
import os.path
import re
import tempfile
import shutil
import subprocess
import logging
import json

import svn.remote


REGEXDOMPATH = re.compile(r"(/uploaded/)+(?P<domain>[a-z0-9]+)(?P<path>[/a-zA-Z.]+)")
REGEXTASKPATH = re.compile(r"(/res/)(?P<domain>[a-z0-9]+)(?P<path>[/a-zA-Z.0-9]+)")

logger = logging.getLogger(__name__)


def save_submission(user_hash, task_uuid, course_hash, submission_url=None, submisssion_fileobj=None, submission_zip=None ):
    base_dir = os.path.dirname(os.path.dirname(__file__))
    submission_save_path = os.path.join(base_dir, task_uuid, user_hash, course_hash, )
    # os.makedirs(base_dir[, mode]) todo save the submission exeption


def check_task(content):
    # todo: check Format-Version
    # check check which Lang + Version is necessary
    # save UUID with Data in Dict -> SQL? or Redis?
    pass


def check_system_svn():
    try:
        subprocess.check_output('svn')
    except subprocess.CalledProcessError:
        return False
    return True

def check_configured_svn(svn_server, svn_repository):
    # SVNURIACCESS Struct
    #    SVN-Server
    #       SVN-REPOSITORY
    #            SVNUSER
    #            SVNPASS
    try:
        if settings.SVNURIACCESS[svn_server][svn_repository] is not None:
            return True
    except KeyError:
            return False


def get_svn_credetials(svn_server, svn_repository):
    """
    get_svn_credetials checks the settings and returns the user and the pass
    :param svn_server: the svn-server
    :param svn_repository: the svn-repository
    :return: svn_user and svn_pass or it raises an exception
    """
    try:
        if 'SVNUSER' in settings.SVNURIACCESS[svn_server][svn_repository] and \
           'SVNPASS' in settings.SVNURIACCESS[svn_server][svn_repository]:
            svn_user = settings.SVNURIACCESS[svn_server][svn_repository].get('SVNUSER')
            svn_pass = settings.SVNURIACCESS[svn_server][svn_repository].get('SVNPASS')
            return svn_user, svn_pass
    except KeyError as err:
        raise err


def svn_to_zip(svn_uri, svn_user, svn_pass, submission_svn_rev=None):
    """
    svn_to_zip
    :param svn_uri: uri of the svn server
    :param svn_user: user
    :param svn_pass: pass
    :param submission_svn_rev:
    :return: fileobj -> zip of submission directory or exception
    """
    submission_directory = "submission-zip"
    remote = svn.remote.RemoteClient(svn_uri, username=svn_user, password=svn_pass)

    tmp_dir = tempfile.mkdtemp()
    remote.export(to_path=os.path.join(tmp_dir, submission_directory), revision=submission_svn_rev)
    to_zip = os.path.join(tmp_dir, submission_directory)

    try:
        tmp_archive = os.path.join(tmp_dir, 'archive')
        root_dir = to_zip
        submission_zip = shutil.make_archive(tmp_archive, 'zip', root_dir)
        submission_zip_fileobj = open(submission_zip, 'rb')
        return submission_zip_fileobj
    except IOError as e:
        raise IOError("IOError:", "An error occured while open zip-file", e)
    except Exception as e:
        raise Exception("SVNException:", "An error occured while creating zip: E125001: Couldn't determine absolute path of '.'")
    finally:
        shutil.rmtree(tmp_dir)


def get_group_rev(submission):
    """
    get_group_rev return a dict of the submission string
    :param submission: string "Gruppe=Value1;Rev=Value2"
    :return: dict of the items before and after = divided by ; or exception
    """
    # remove last;
    submission = submission.rstrip(';')
    try:
        submission_dict = dict(item.split("=") for item in submission.split(";"))
    except KeyError:
        raise KeyError("The submission must be in the format: Gruppe=<integer>;Rev=<integer>")
    except ValueError:
        raise ValueError("The submission must be in the format: Gruppe=<integer>;Rev=<integer>")
    return submission_dict


@csrf_exempt
def grade_api_v1(request, fw=None, fw_version=None):
    """
    main function: coordinates every call
        - gets the submission:
            submission as textfield
            submission as file
            submission as svn-directory
        - gets the
    :param request:
    :param fw:
    :param fw_version:
    :return:
    """

    # Todo add language python;)

    logger.debug('HTTP_USER_AGENT: ' + request.META.get('HTTP_USER_AGENT') +
                '\nHTTP_HOST: ' + request.META.get('HTTP_HOST') +
                '\nrequest.path: ' + request.path +
                '\nrequest.POST:' + str(list(request.POST.items())))

    # debugging uploaded files
    for f in request.FILES.getlist('file'):
        logger.debug("request.Files: " + str(f))

    if not request.POST:
        return HttpResponse(answer_format_template(award="ERROR", message="No POST-Request attached"))
    else:
        answer_format_form = request.POST.get("answer-format")
        task_repo = request.POST.get("task-repo")
        submission = request.POST.get("submission")
        exercise_id = request.POST.get("exercise_id")
        task_path = request.POST.get("task-path")
        submission_filename = request.POST.get("submission-filename")
        submission_uri = request.POST.get("submission-uri")
        submission_uri_type = request.POST.get("submission-uri-type")
        external_course_book = request.POST.get("extCoursebook")
        proforma_zip = None
        task_uuid = None
        task_uuid = request.POST.get("uuid")

        ## handling Files

        if request.FILES:
            try:
                if request.FILES['task-file'].name:
                    proforma_zip = dict()
                    proforma_zip[request.FILES['task-file'].name] = request.FILES['task-file']
            except MultiValueDictKeyError:
                # no task-file
                pass

        if not proforma_zip:
            if not task_repo:
                return HttpResponse(answer_format_template(award="ERROR", message="No repository specified",
                                                           format=answer_format_form))
            if not task_path:
                return HttpResponse(answer_format_template(award="ERROR", message="No task repository to task attached",
                                                           format=answer_format_form))

        # studip needs an exerciseID -> todo better solution
        if exercise_id:
            task_path = task_path[:-2] + "&exercise_id=" + exercise_id

        if submission:
            if not (submission and submission_filename):
                return HttpResponse(answer_format_template(award="ERROR", message="No submission_filename or submission",
                                                           format=answer_format_form))
        elif submission_uri or submission_uri_type:
            if submission_uri_type == "svn-server":
                pass
            elif not(submission_uri and submission_uri_type):
                return HttpResponse(answer_format_template(award="ERROR", message="If you use a submission-uri define"
                                                                        "type with submission-uri-type: web or svn",
                                                           format=answer_format_form))
        elif request.FILES['submission-file'].name:
            try:
                submission_zip = dict()
                logger.debug("request.FILES['submission-file'].name: " + request.FILES['submission-file'].name)
                submission_zip[request.FILES['submission-file'].name] = request.FILES['submission-file']
            except Exception:
                return HttpResponse(answer_format_template(award="ERROR", message="Error while reading submission-file",
                                                           format=answer_format_form))
        else:
            # logger.error("request.FILES.keys(): " + request.FILES.keys())
            return HttpResponse(answer_format_template(award="ERROR", message="No submission_uri, submission or submissions_file."
                                                                    " Please upload only one file",
                                                       format=answer_format_form))

        # SVN-URI = SVN-Server + submission_svn_repository + submission_svn_group
        if submission_uri_type == "svn-server":
            if not check_system_svn():
                HttpResponse(answer_format_template(award="ERROR", message="svn is not installed on the server"))
            lc_submission = request.POST.get("student_response")
            submission_svn_repository = request.POST.get("svn-repository")
            submission_svn_path = request.POST.get("svn-path")

            if not submission_svn_path:
                return HttpResponse(answer_format_template(award="ERROR", message="Please add a svn-path if you use "
                                                                        "svn-server", format=answer_format_form))
            if not submission_svn_repository:
                return HttpResponse(answer_format_template(award="ERROR", message="Please add a svn-repository if you use "
                                                                        "svn-server", format=answer_format_form))
            if lc_submission:
                try:
                    submission_dict = get_group_rev(lc_submission)
                except KeyError as err:
                    return HttpResponse(answer_format_template(award="ERROR", message=err, format=answer_format_form))
                except ValueError as err:
                    return HttpResponse(answer_format_template(award="ERROR", message=err, format=answer_format_form))
                # we expect: Gruppe=<int>;Rev=<int>;
                if 'Gruppe' not in submission_dict:
                    return HttpResponse(answer_format_template(award="ERROR", message="There as a problem with your group-name.",
                                                               format=answer_format_form))
                try:
                    submission_svn_group = int(submission_dict.get('Gruppe'))
                except Exception:
                    return HttpResponse(answer_format_template(award="ERROR", message="There as a problem with your group-name, "
                                                                            "revision, please read "
                                                                            "the description - all must be int",
                                                               format=answer_format_form))
            else:
                return HttpResponse(answer_format_template(award="ERROR", message="The group is missing",
                                                           format=answer_format_form))

        elif submission_uri_type == "svn":
            if not check_system_svn():
                return HttpResponse(answer_format_template(award="ERROR", message="svn is not installed on the server"))
            submission_svn_user = request.POST.get("submission-svn-user")  # could also be a group name
            if not submission_svn_user:
                return HttpResponse(answer_format_template(award="ERROR", message="Please set a submission-svn-user and a "
                                                                        "submission-svn-revision",
                                                           format=answer_format_form))

        if external_course_book:
            if settings.EXTCOURSEBOOK.get(external_course_book):
                labor_id = request.POST.get("laborId")
                aufgaben_id = request.POST.get("aufgabenId")
                if not (labor_id and aufgaben_id):
                    return HttpResponse(answer_format_template(award="ERROR", message="If you use an external gradebook add "
                                                                            "laborId and aufgabenId",
                                                               format=answer_format_form))
            else:
                return HttpResponse(answer_format_template(award="ERROR", message="Your external Coursebook is not listed added "
                                                                        "in the middleware",
                                                           format=answer_format_form))

    # todo: get task from repository or from cache
    # check cache
    try:
        pass
    except Exception as e:
        return HttpResponse(answer_format_template(award="ERROR", message="get_task_from_externtal_server: " + str(type(e)) + str(e.args),
                                                   format=answer_format_form))
    # check task-send
    if proforma_zip:
        try:
            for filename, file_obj in proforma_zip.items():
                task_filename = filename
                content = file_obj
        except Exception as e:
            return HttpResponse(answer_format_template(award="ERROR",
                                                       message="read post-request task-file: "
                                                       + str(type(e))+str(e.args),
                                                       format=answer_format_form))

    # todo: task_data = check_task(content)
    # todo: 1. check if proglang is supported ->
    # todo: 2. check if checker + version is avail -> send to grader
    # -> chosenGrader
    # create Task and get id
    try:
        if task_path:
            task_filename = os.path.basename(task_path)
        task_id = create_external_task(content_file_obj=content, server=settings.GRADERV, taskFilename=task_filename,
                                       formatVersion=answer_format_form)
    except Exception as e:
        return HttpResponse(answer_format_template(award="ERROR", message="create_external_task: " + str(type(e)) + str(e.args),
                                                   format=answer_format_form))
    # send student-submission
    if submission:
        try:
            grade_result = sendTextfieldPraktomat(studentResponse=submission, studentFilename=submission_filename,
                                                  server=settings.GRADERV, taskID=task_id)
        except Exception as e:
            return HttpResponse(answer_format_template(award="ERROR", message=str(e)))
        return HttpResponse(grade_result)

    elif submission_uri or submission_uri_type:
        # todo: allow only allowed domains?
        if submission_uri_type == "web":
            # check structure and content of externalStudentFilePathes
            try:
                studentDownloadDomain, studentSubmissionFiles = checkStudentPath(submission_uri)
            except ImportError as e:
                return HttpResponse(answer_format_template(award="ERROR", message=e.args))
            except Exception as e:
                return HttpResponse(answer_format_template(award="ERROR", message=str(e)))

            # get files from server
            try:
                files = getStudentSubmissionFile(filePathList=studentSubmissionFiles, domain=studentDownloadDomain)
            except IOError as e:
                return HttpResponse(answer_format_template(award="ERROR", message="getStudentSubmissionFile: " + e.args))
            except Exception as e:
                return HttpResponse(answer_format_template(award="ERROR", message=str(e)))

            # start grading
            try:
                grade_result = send_submission2external_grader(request, settings.JAVAGRADER, task_id, files)
            except Exception as e:
                return HttpResponse(answer_format_template(award="ERROR", message=str(e)))
            return HttpResponse(grade_result)
        elif submission_uri_type == "svn-server":
            submission_svn_server = "https://code.localhost"

            if not check_configured_svn(svn_repository=submission_svn_repository, svn_server=submission_svn_server):
                logger.exception("check_configured_svn\r\n" + str(submission_svn_repository) + "  " +
                                 str(submission_svn_server))
                return HttpResponse(answer_format_template(award="ERROR", message="the configured svn-server and repository is "
                                                                        "not known to the middleware"))
            try:
                submission_svn_user, submission_svn_pass = get_svn_credetials(svn_repository=submission_svn_repository,
                                                                          svn_server=submission_svn_server)
            except KeyError as err:
                return HttpResponse(answer_format_template(award="ERROR", message="There was a problem getting the user and the "
                                                                        "pass for the svn"))
            # get Task svn_to_zip(svn_uri=None, submission_svn_rev=None, svn_directory=None):
            # SVN-URI = SVN-Server + submission_svn_repository + submission_svn_group
            # start grading todo gruppe -> Gruppe
            path = "svn/" + str(submission_svn_repository) + "/" + "Gruppe" + str(submission_svn_group) + "/" + \
                   str(submission_svn_path) + "/src"
            submission_svn_uri = urllib.parse.urljoin(submission_svn_server, path)
            try:
                student_submission_zip_obj = svn_to_zip(svn_uri=submission_svn_uri, svn_user=submission_svn_user,
                                                        svn_pass=submission_svn_pass)
            except IOError as e:
                return HttpResponse(answer_format_template(award="ERROR", message=str(e)))
            except ValueError as e:
                return HttpResponse(answer_format_template(award="ERROR", message="Could not connect to svn -> remote.info got exception" + str(e)))
            except Exception as e:
                return HttpResponse(answer_format_template(award="ERROR", message=str(e)))
            # start grading todo gruppe -> Gruppe
            submission_zip = {"Gruppe" + str(submission_svn_group) + ".zip": student_submission_zip_obj}
            # submission_zip = {'submission.zip': student_submission_zip_obj}
            try:
                grade_result = send_submission2external_grader(request=request, server=settings.GRADERV, taskID=task_id,
                                                               files=submission_zip)
            except Exception as e:
                return HttpResponse(answer_format_template(award="ERROR", message=str(e)))
            # if everything works we should end here
            if external_course_book:
                # todo should be startet with another thread -> parallel
                send_result_to_gradebook(grade_result, labor_id=labor_id, aufgaben_id=aufgaben_id,
                                         group=submission_svn_group, external_course_book_uri=external_course_book)
            return HttpResponse(grade_result)
        else:
            return HttpResponse(answer_format_template(award="ERROR", message="submission-uri-type is not known",
                                                       format=answer_format_form))
    elif submission_zip:
        for fname, ffile in request.FILES.items():
            submission_upload_filename = request.FILES[fname].name  # todo: only works with one file and why no chunks?
            uploaded_file_obj = ffile.read()  # take the first element
            uploaded_file = {submission_upload_filename: uploaded_file_obj}
        #uploaded_file_obj = request.FILES[0].read()  # take the first element
        try:
            grade_result = send_submission2external_grader(request, settings.GRADERV, task_id, uploaded_file)
        except Exception as e:
            return HttpResponse(answer_format_template(award="ERROR", message=str(e)))
        return HttpResponse(grade_result)
    else:
        return HttpResponse(answer_format_template(award="ERROR", message="No submission nor submission-uri is set",
                                                   format=answer_format_form))


@csrf_exempt  # disable csrf-cookie
def grade_api_v2(request,):
    response = api_v2.grade_api_v2(request,)
    return response


def send_result_to_gradebook(grade_result, labor_id, aufgaben_id, group, external_course_book_uri):

    status = False
    comment = ""
    xapi_auth_token = settings.EXTCOURSEBOOK.get(external_course_book_uri)
    headers = {'Content-type': 'application/json', 'X-API-Auth-Token': xapi_auth_token}

    match = re.search('<awarddetail>(?P<award>.+?)?<\/awarddetail>', grade_result)
    if match.group('award') == "EXACT_ANS":
        status = True

    json_data = {
                "labor": labor_id,
                "aufgabe": aufgaben_id,
                "data": {
                    "gruppe-" + str(group): {
                        "status": status,
                        "kommentar": comment
                    }
                }
            }
    try:
        r = requests.put(url=external_course_book_uri, headers=headers, json=json_data, verify=False)
        logger.info("json_data:" + json.dumps(json_data))
        logger.info("status_code: " + str(r.status_code) + "content: " + str(r.content))
    except Exception as e:
        logger.error("Exception: send_result_to_gradebook: " + str(type(e)) + str(e.args))


def sendTextfieldPraktomat(studentResponse, studentFilename, server, taskID):
    post_data = [("LONCAPA_student_response", studentResponse), ]
    payload = {'LONCAPA_student_response': studentResponse}
    # ToDo : simplify URI for grading
    serverpath = urllib.parse.urlparse(server)  # todo trailing slashes
    if settings.OUTPUTXML:
        domainnOutput = "textfield/lcxml"
    else:
        domainnOutput = "textfield/LC_2.10.1"
    path = "/".join([str(x).rstrip('/') for x in [serverpath.path, domainnOutput,
                                                       str(studentFilename), str(taskID)]])
    grading_url = urllib.parse.urljoin(server, path)
    result = requests.post(url=grading_url, data=payload)

    if result.status_code == requests.codes.ok:
        return result.text
    else:
        return HttpResponse(answer_format_template(award="ERROR", message=result.text))


def send_submission2external_grader(request, server, taskID, files):
    serverpath = urllib.parse.urlparse(server)
    domainOutput = "external_grade/proforma/v1/task/"
    path = "/".join([str(x).rstrip('/') for x in [serverpath.path, domainOutput, str(taskID)]])
    gradingURL = urllib.parse.urljoin(server, path)
    result = requests.post(url=gradingURL, files=files)
    if result.status_code == requests.codes.ok:
        return result.text
    else:
        return HttpResponse(answer_format_template(award="ERROR", message=result.text))


def create_external_task(content_file_obj, server, taskFilename, formatVersion):

    FILENAME = taskFilename

    try:
        files = {FILENAME: open(content_file_obj.name, 'rb')}
    except IOError:  #
        files = {FILENAME: content_file_obj}
    url = urllib.parse.urljoin(server, 'importTaskObject/V1.01')
    result = requests.post(url, files=files)

    if result.headers['Content-Type'] == 'application/json':
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
        message = "Error while creating task on grader " + result.text
        raise IOError(message)


def getStudentSubmissionFile(filePathList, domain):
    listOfSolutionFiles = []
    with requests.Session() as s:
        for filePath in filePathList:
            url = domain + '/uploaded/' + filePath
            # todo:parallel downloads? http://docs.python-requests.org/en/v0.10.6/user/advanced/#asynchronous-requests
            try:
                req_get = requests.Request(method='GET', url=url)
                prepped = s.prepare_request(req_get)
                response = s.send(prepped, verify=False)

                if response.status_code != 200:
                    message = "Could not download submission file from server: " + url
                    raise IOError(message)
                else:
                    try:
                        with tempfile.NamedTemporaryFile(delete=False) as submissionFile:
                            listOfSolutionFiles.append(submissionFile.write(response.content))
                    except Exception:
                        raise Exception("Error while saving submission file in tempfile")

            except Exception:
                raise Exception("An Error occured while downloading studentsubmission")
    return listOfSolutionFiles


@csrf_exempt
def get_version(request):
    contents = ""
    try:
        with open("VERSION", "r") as f:
            contents = f.read()
    except Exception:
        return HttpResponse("Could not read version")
    return HttpResponse(contents)
