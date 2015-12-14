from httplib2 import HttpLib2Error

class IllegalArgumentError(ValueError):
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return repr(self.message)

class RestError(HttpLib2Error):
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return repr(self.message)

class JenkinsException(IllegalArgumentError, RestError, IOError):
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return repr(self.message)

def __check_http_response_error__(url, resp, content):
    if int(resp['status']) < 200 or int(resp['status']) > 399:
        raise JenkinsException("%s: %s %s" % (url, resp['status'], "-- "+content))

##def check_http_response_error(*args):
##   if int(resp['status']) < 200 or int(resp['status']) > 399:
##        raise JenkinsException("%s: %s %s" % (url, resp['status'], "-- "+content))