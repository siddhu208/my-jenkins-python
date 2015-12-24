import httplib2
from exceptions_jenkins import JenkinsException, __check_http_response_error__
import base64

def __get_jenkins_http_object__(url, username=None, password=None):
    try:
        if not url.endswith('/'):
            url = url+"/"
        h = httplib2.Http(cache=None)

        headers = dict()
        if username and password:
            cred = base64.b64encode("{0}:{1}".format(username, password).encode('utf-8')).decode()
            headers = {'Authorization': 'Basic ' + cred}

        resp, content = h.request(url, method='HEAD', headers=headers)
        __check_http_response_error__("HEAD: %s" % url, resp, content)
        return (h, headers)
    except httplib2.HttpLib2Error as he:
        raise JenkinsException(he.message)
    except Exception as e:
        raise JenkinsException(e.message)
