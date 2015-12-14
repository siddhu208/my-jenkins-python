import httplib2
from json import loads
from exceptions_jenkins import JenkinsException, __check_http_response_error__, check_http_response_error
from os import getcwd as os_getcwd, access as os_access, W_OK
from os.path import join as os_join, isabs as os_isabs
import base64

def __check_url_exists__(url, username=None, password=None):
    try:
        h = httplib2.Http(cache=None)

        headers = dict()
        if username is not None and password is not None:
            cred = base64.b64encode("{0}:{1}".format(username, password).encode('utf-8')).decode()
            headers = {'Authorization': "Basic %s" % cred}

        print "In check url: -%s-, -%s- and -%s-" % (url, username, password)
        print headers
        h.follow_all_redirects = True
        headers = h.request(url, "HEAD", headers=headers)[0]
        status = int( headers['status'] )
        print status
        if status >= 200 and status <= 399:
            return True
        else:
            return False
            #raise JenkinsException("Error pinging url %s!!. Received http status %s" % (url, status))

    except httplib2.HttpLib2Error as e:
        return False
        #raise JenkinsException("ERROR!! Failed connecting to jenkins url %s. Error message is:\n %s" % (url, e.message))

def list_jobs(jenkinsurl, username=None, password=None):
    try:
        if not __check_url_exists__(jenkinsurl, username, password):
            raise JenkinsException("Unable to ping url {0}".format(jenkinsurl))
        h = httplib2.Http(cache=None)

        headers = dict()
        if username is not None and password is not None:
            cred = base64.b64encode("{0}:{1}".format(username, password).encode('utf-8')).decode()
            headers = {'Authorization': "Basic %s" % cred}

        h.follow_all_redirects = True
        resp, content = h.request(jenkinsurl+"/api/json", "GET", headers=headers)
        check_http_response_error("GET: "+jenkinsurl+"/api/json", resp, content)

        return [jobInfo['name'].encode('ASCII') for jobInfo in loads(content)['jobs']]

    except httplib2.HttpLib2Error as e:
        raise JenkinsException(e.message)

class jenkins(object):

    def __init__(self, url, username=None, password=None):
        if not (url.startswith('http://') or url.startswith('https://')):
            url = 'http://'+url
        self.url = url

        self.user = username
        self.password = password
        self.http_ = httplib2.Http(cache=None)
        self.http_.follow_all_redirects = True

        print self.user
        print self.password
        #__check_url_exists__(self.url, self.user, self.password)

        self.headers = dict()
        if self.user is not None and self.password is not None:
            cred = base64.b64encode("{0}:{1}".format(self.user, self.password).encode('utf-8')).decode()
            self.headers = {'Authorization': "Basic %s" % cred}

    def get_jobs(self, context=''):
        return list_jobs(self.url+"/"+context, self.user, self.password)

    def enable_jobs(self, *jobs):
        if len(jobs) == 0:  raise JenkinsException('No Jobs provided.')
        jobs_status = list()

        for job in jobs:
            try:
                if not __check_url_exists__(self.url+"/job/"+job, self.user, self.password):
                    jobs_status.append({"job": job, "message": "No such job: "+self.url+"/job/"+job, "success": False})
                else:
                    resp, content = self.http_.request(self.url+"/job/"+job+"/enable", "POST", headers=self.headers)
                    check_http_response_error("POST: "+self.url+"/job/"+job+"/enable", resp, content)
                    jobs_status.append({"job": job, "message": self.url+"/job/"+job, "success": True})
            except JenkinsException as je:
                jobs_status.append({"job": job, "message": je.message, "success": False})

        return jobs_status

    def disable_jobs(self, *jobs):
        if len(jobs) == 0:  raise JenkinsException('No Jobs provided.')
        jobs_status = list()

        for job in jobs:
            try:
                if not __check_url_exists__(self.url+"/job/"+job):
                    jobs_status.append({"job": job, "message": "No such job: "+self.url+"/job/"+job, "success": False})
                else:
                    resp, content = self.http_.request(self.url+"/job/"+job+"/disable", "POST", headers=self.headers)
                    check_http_response_error("POST: "+self.url+"/job/"+job+"/disable", resp, content)
                    jobs_status.append({"job": job, "message": None, "success": True})
            except JenkinsException as je:
                jobs_status.append({"job": job, "message": je.message, "success": False})

        return jobs_status

    def delete_jobs(self, *jobs):
        if len(jobs) == 0:  raise JenkinsException('No Jobs provided.')
        jobs_status = list()
        for job in jobs:
            try:
                if not __check_url_exists__(self.url+"/job/"+job):
                    jobs_status.append({"job": job, "message": "No such job: "+self.url+"/job/"+job, "success": False})
                else:
                    resp, content = self.http_.request(self.url+"/job/"+job+"/doDelete", "POST", headers=self.headers)
                    check_http_response_error("POST: "+self.url+"/job/"+job+"/doDelete", resp, content)
                    jobs_status.append({"job": job, "message": None, "success": True})
            except JenkinsException as je:
                jobs_status.append({"job": job, "message": je.message, "success": False})

        return jobs_status

    def get_job_config_xml(self, job, outputfile=''):
        if not __check_url_exists__(self.url+"/job/"+job):
            raise JenkinsException("No such job: "+self.url+"/job/"+job)

        outputfile = outputfile.strip()

        if outputfile == '':
            outputfile = os_join(os_getcwd(), 'config_'+job+'.xml')
        elif not os_isabs(outputfile):
            outputfile = os_join(os_getcwd(), outputfile)

        try:
            resp, content = self.http_.request(self.url+"/job/"+job+"/config.xml", "GET", headers=self.headers)
        except httplib2.HttpLib2Error as e:
            raise JenkinsException(e.message)

        check_http_response_error("POST: "+self.url+"/job/"+job+"/config.xml", resp, content)

        try:

            with open(outputfile, "wb") as f:
                f.write(content)

        except IOError as e:
            raise JenkinsException(e)

        return outputfile

    def create_job(self, name='', context='', configxml=None, configxmlfile=None, copyfrom=None):
        if name == '':
            raise JenkinsException('Jenkins new job name is not supplied.')
        else:
            if __check_url_exists__(self.url+"/job/"+name):
                raise JenkinsException("A job with name {0} already exists at {1}".format(name, self.url))
        if not [copyfrom, configxml, configxmlfile].count(None) == 2:
            raise JenkinsException("Ambiguous arguments: Only one of copyfrom, configxml, configxmlfile should be provided.")

        if copyfrom is not None and not __check_url_exists__(self.url+"/job/"+copyfrom):
            raise JenkinsException("Could not find job {0} in {1}".format(copyfrom, self.url))

        headers_new = self.headers.copy()
        headers_new.update({'Content-Type': 'application/xml'})
        def creater(xml):
            try:
                resp, content = self.http_.request(self.url+"/"+context+"/createItem?name="+name, method="POST",
                                                   headers=headers_new, body=xml)
            except httplib2.HttpLib2Error as e:
                raise JenkinsException(e.message)
            check_http_response_error("POST: "+self.url+"/"+context+"/createItem?name="+name, resp, content)
            return True

        if configxmlfile is not None:
            with open(configxmlfile) as f:
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
            check_http_response_error("POST: "+url_, resp, content)

        return self.url+"/"+context+"/job/"+name

    def add_job_to_view(self, view, *jobs):
        if len(jobs) == 0:
            raise JenkinsException('No Jobs provided.')
        jobs_status = list()
        for job in jobs:
            try:
                if not __check_url_exists__(self.url+"/job/"+job):
                    jobs_status.append({"job": job, "message": "No such job: "+self.url+"/job/"+job, "success": False})
                else:
                    params = httplib2.urllib.urlencode({"name": job})
                    resp, content = self.http_.request("{0}/view/{1}/addJobToView?{2}".format(self.url, view, params),
                                                       "POST", headers=self.headers)
                    check_http_response_error("POST: "+self.url+"/job/"+job+"/doDelete", resp, content)
                    jobs_status.append({"job": job, "message": None, "success": True})
            except JenkinsException as je:
                jobs_status.append({"job": job, "message": je.message, "success": False})

        return jobs_status
