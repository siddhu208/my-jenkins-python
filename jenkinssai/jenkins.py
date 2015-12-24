from json import loads
from exceptions_jenkins import JenkinsException, __check_http_response_error__
import httplib2
import os
from jenkinsHttpObject import __get_jenkins_http_object__

def list_jobs(url, username=None, password=None):
    http_, headers = __get_jenkins_http_object__(url, username, password)

    url = "{0}/api/json".format(url)
    try:
        resp, content = http_.request(url, "GET", headers=headers)
    except httplib2.HttpLib2Error as he:
        raise JenkinsException(he.message)

    __check_http_response_error__("GET: {0}".format(url), resp, content)

    return [jobInfo['name'].encode('ASCII') for jobInfo in loads(content)['jobs']]

class jenkins(object):
    def __init__(self, url, username=None, password=None):
        self.url = url
        self.username = username
        self.password = password

        self.http_, self.base_headers = __get_jenkins_http_object__(self.url, self.username, self.password)

    def get_jobs(self, context=''):
        if not context == '':
            self.url = "%s/context"
        return list_jobs(self.url if context == '' else "{0}/{1}".format(self.url, context), self.username, self.password)

    def enable_job(self, name):
        try:
            url_job = "{0}/job/{1}/enable".format(self.url, name)
            resp, content = self.http_.request(url_job, method="POST", headers=self.base_headers)
        except httplib2.HttpLib2Error as he:
            raise JenkinsException(he.message)

        __check_http_response_error__("POST: {0}".format(url_job), resp, content)
        return True

    def disable_job(self, name):
        try:
            url_job = "{0}/job/{1}/disable/".format(self.url, name)
            resp, content = self.http_.request(url_job, method="POST", headers=self.base_headers)
        except httplib2.HttpLib2Error as he:
            raise JenkinsException(he.message)

        __check_http_response_error__("POST: {0}".format(url_job), resp, content)
        return True

    def delete_job(self, name):
        try:
            url_job = "{0}/job/{1}/doDelete".format(self.url, name)
            resp, content = self.http_.request(url_job, method="POST", headers=self.base_headers)
        except httplib2.HttpLib2Error as he:
            raise JenkinsException(he.message)

        __check_http_response_error__("POST: {0}".format(url_job), resp, content)
        return True

    def get_job_config_xml(self, job, outputfile=''):

        outputfile = outputfile.strip()

        if outputfile == '':
            outputfile = os.path.join(os.getcwd(), 'config_'+job+'.xml')
        elif not os.path.isabs(outputfile):
            outputfile = os.path.join(os.getcwd(), outputfile)

        url_job = "{0}/job/{1}/config.xml".format(self.url, job)
        try:
            resp, content = self.http_.request(url_job, method="GET", headers=self.base_headers)
        except httplib2.HttpLib2Error as e:
            raise JenkinsException(e.message)

        __check_http_response_error__("POST: "+url_job, resp, content)

        try:
            with open(outputfile, "wb") as f:
                f.write(content)

        except IOError as e:
            raise JenkinsException(e)

        return outputfile

    def create_job(self, name='', context='', configxml=None, configxmlfile=None, copyfrom=None):
        if name == '':
            raise JenkinsException('Jenkins new job name is not supplied.')

        if [configxml, configxmlfile, copyfrom].count(None) == 3:
            raise JenkinsException("None of the arguments: configxml, configxmlfile, copyfrom are provided.")
        elif not [copyfrom, configxml, configxmlfile].count(None) == 2:
            raise JenkinsException("Ambiguous arguments: Only one of copyfrom, configxml, configxmlfile should be provided.")

        headers_new = self.base_headers.copy()
        headers_new.update({"Content-Type": "application/xml; charset=\"UTF-8\""})

        def creater(xml):
            try:
                params = httplib2.urllib.urlencode({'name': name})
                resp, content = self.http_.request(self.url+"/"+context+"/createItem?"+params, method="POST",
                                                   headers=headers_new, body=xml.encode('ascii', 'xmlcharrefreplace'))
            except httplib2.HttpLib2Error as e:
                raise JenkinsException(e.message)
            __check_http_response_error__("POST: "+self.url+"/"+context+"/createItem?name="+name, resp, content)
            return True

        if configxmlfile is not None:
            #with codecs.open(configxmlfile, 'r', encoding='utf-8') as f:
            with open(configxmlfile, 'r') as f:
                creater(f.read())

        elif configxml is not None:
            creater(configxml)
        elif copyfrom is not None:
            try:
                params = httplib2.urllib.urlencode({'name': name, 'mode': 'copy', 'from': copyfrom})
                url_ = "{0}/{1}/createItem?{2}".format(self.url, context, params)
                resp, content = self.http_.request(url_, method="POST", headers=headers_new)
            except httplib2.HttpLib2Error as e:
                raise JenkinsException(e.message)
            __check_http_response_error__("POST: "+url_, resp, content)

        return self.url+"/"+context+"/job/"+name