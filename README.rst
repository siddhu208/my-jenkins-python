jenkinsai
---------
To use (with caution), simply do::

    >>> import jenkinsai
    >>> dir(jenkinssai)

I have also included a cli for jenkins. To use, run jenkins_siddhu.py.
Run with --help to see all options.

$ python jenkins_siddhu.py
Usage: jenkins_siddhu.py [OPTIONS] COMMAND [ARGS]...

  This is a jenkins parser script developed by Sai Siddartha Thotapalli
  mostly to do the redundant devops operations.

  To make it easy and not to remember various jenkins instances with their usernames and passwords, you may use a yaml
  file and supply it to the script; see --help on how to supply this.

  Note: Credentials supplied in comand line takes precedence over the yaml file.

  Note: migrate command does not look for config.yaml. It needs credentials to be passed manually from command-line.

  YAML file should look like this:
  jenkinsurl.mycompany.com:
    user: m320921
    pass: apikeyORpassword
  172.17.0.159:
    user: m320921
    pass: apikeyORpassword
  etc...
  where jenkinsurl is http://jenkinsurl.mycompany.com:8080/jenkins. The main key has to be the hostname of jenkins.

  If the url is http://www.jenkinsurl..., use the key as www.jenkinsurl.

Options:
  -c, --jenkins-config FILENAME  Jenkins configuration yaml file containing
                                 jenkins username and passwords or set
                                 environment variable JENKINS_CONFIG_YAML_FILE
                                 with path to the yaml file
  --help                         Show this message and exit.

Commands:
  jobs          Manages jobs
  migrate       Copy jobs from one jenkins to another and...
  plugins       Manages Plugins
  release-copy  Copy jobs from one view to another, may be...
