from exceptions_jenkins import JenkinsException, __check_http_response_error__
import httplib2
from json import loads
from jenkinsHttpObject import __get_jenkins_http_object__

class plugins(object):
    def __init__(self, url, username=None, password=None):
        self.url = url
        self.username = username
        self.password = password

        self.http_, self.base_headers = __get_jenkins_http_object__(self.url, self.username, self.password)

    def list_installed(self):

        try:
            params = httplib2.urllib.urlencode({"depth": 1, "xpath": "/*/*/shortName|/*/*/version", "wrapper": "plugins"})
            ### url_ = "{0}/pluginManager/api/json?depth=1&xpath=/*/*/shortName|/*/*/version&wrapper=plugins".format(self.url)
            url_ = "{0}/pluginManager/api/json?{1}".format(self.url, params)
            resp, content = self.http_.request(url_, method="GET", headers=self.base_headers)
        except httplib2.HttpLib2Error as e:
            raise JenkinsException(e.message)

        __check_http_response_error__("GET: "+url_, resp, content)
        try:
            return {item['shortName'].encode('ascii'): item['version'].encode('ascii') for item in loads(content)['plugins']}
        except Exception as e:
            raise JenkinsException(e.message)