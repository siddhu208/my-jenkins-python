from json import dumps
import click
import jenkinssai
import os
import time
from yaml import load as yaml_load, YAMLError

def getCredsFromYaml(yaml_file, jenkins_url):

    try:
        with open(yaml_file) as f:
            conf = yaml_load(f)
            jenkins_host = jenkins_url.split('http://')[-1].split('https://')[-1].split('/')[0].split(':')[0]
            if conf.has_key(jenkins_host):
                return (conf[jenkins_host]['user'], conf[jenkins_host]['pass'])

        return(None, None)
    except IOError as e:
        print "Error reading file ", yaml_file
        print str(e.message)
        exit(2)
    except YAMLError, exc:
        print "Error in yaml file ", yaml_file
        print exc
        exit(2)
    except Exception as e:
        print e.message
        exit(2)

def getCreds(yaml_file, jenkins_url, user_opt, pass_opt):

    if user_opt is not None and pass_opt is not None:
        return user_opt, pass_opt
    elif user_opt is not None and pass_opt is None:
        pass_opt = os.environ.get('JENKINS_PASSWORD', '')
        if pass_opt == '':
            pass_opt = click.prompt("Enter Jenkins Password", type=str, hide_input=True)
    elif user_opt is None and pass_opt is not None:
        click.echo("ERROR: Password is provided, but no username is found!!")
        click.echo("Check for environment variables if you have not provided the password via command line..")
        exit(2)
    elif user_opt is None and yaml_file is not None:
        user_opt, pass_opt = getCredsFromYaml(yaml_file, jenkins_url)
    else:
        user_opt, pass_opt = None, None
    return user_opt, pass_opt


@click.group()
@click.option('-c', '--jenkins-config', 'yaml_config_file', envvar='JENKINS_CONFIG_YAML_FILE', type=click.File('r'),
              help='Jenkins configuration yaml file containing jenkins username and passwords or set environment variable JENKINS_CONFIG_YAML_FILE with path to the yaml file')
@click.pass_context
def basecli(ctx, yaml_config_file):
    """
    This is a jenkins parser script developed by Sai Siddartha Thotapalli mostly to do the redundant devops operations.

    \b
    To make it easy and not to remember various jenkins instances with their usernames and passwords, you may use a yaml
    file and supply it to the script; see --help on how to supply this.
    \b
    Note: Credentials supplied in comand line takes precedence over the yaml file.
    \b
    Note: migrate command does not look for config.yaml. It needs credentials to be passed manually from command-line.

    \b
    YAML file should look like this:
    jenkinsurl.mycompany.com:
      user: m320921
      pass: apikeyORpassword
    172.17.0.159:
      user: m320921
      pass: apikeyORpassword
    etc...
    where jenkinsurl is http://jenkinsurl.mycompany.com:8080/jenkins. The main key has to be the hostname of jenkins.
    \b
    If the url is http://www.jenkinsurl..., use the key as www.jenkinsurl.
    """
    config_file = None
    if yaml_config_file is not None:
        config_file = yaml_config_file.name
        if not os.path.isabs(config_file):
            config_file = os.path.join(os.getcwd(), config_file)
    ctx.obj['yaml_config_file'] = config_file

@basecli.group()
@click.pass_context
def jobs(ctx):
    """Manages jobs"""

@jobs.command('list')
@click.pass_context
@click.option('-J', '--jenkins', required=True, help="Jenkins URL or set environment variable JENKINS_URL", envvar="JENKINS_URL")
@click.option('-j', '--json', 'json_opt', is_flag=True, help="output in json format")
@click.option('-s', '--shell', 'shell_opt', is_flag=True,
              help="output in a format that may be useful in shell scripting, output may not be as you like it")
@click.option('-u', '--user', 'user_opt', envvar="JENKINS_USERNAME",
              help="Jenkins User Name or set the environment variable JENKINS_USERNAME")
@click.option('-p', '--password', 'pass_opt', envvar="JENKINS_PASSWORD",
              help="Jenkins Password or set the environment variable JENKINS_PASSWORD. We will prompt for password, if not supplied")
def list(ctx, jenkins, json_opt, shell_opt, user_opt, pass_opt):
    """Lists jobs for the jenkins url provided"""

    user_opt, pass_opt = getCreds(ctx.obj['yaml_config_file'], jenkins, user_opt, pass_opt)

    if not (json_opt or shell_opt):
        click.echo('=== Jobs at %s:' % jenkins)

    if json_opt and shell_opt:
        click.echo("ERROR!!")
        click.echo("Ambiguous flags. shell and json flags can not be used together!!")
        click.echo("")
        exit(2)

    try:
        j = jenkinssai.jenkins(jenkins, user_opt, pass_opt)
        names = j.get_jobs()
    except Exception as e:
        print "\t",
        print e.message
        click.echo("")
        exit(2)

    if json_opt:
        click.echo(dumps(names, indent=4))
    elif shell_opt:
        click.echo('\n'.join(names))
    else:
        for job in names:
            click.echo("\t%s" % job)

    if not (json_opt or shell_opt):
        click.echo("")

@jobs.command('create')
@click.pass_context
@click.argument('jobname', nargs=-1, required=True)
@click.option('-J', '--jenkins', required=True, help="Jenkins URL or set environment variable JENKINS_URL", envvar="JENKINS_URL")
@click.option('-c', '--config', type=click.File('r'), help="path to config.xml file")
@click.option('-f', '--copyfrom', help="job to copy from")
@click.option('-u', '--user', 'user_opt', envvar="JENKINS_USERNAME",
              help="Jenkins User Name or set the environment variable JENKINS_USERNAME")
@click.option('-p', '--password', 'pass_opt', envvar="JENKINS_PASSWORD",
              help="Jenkins Password or set the environment variable JENKINS_PASSWORD. We will prompt for password, if not supplied")
def create(ctx, jenkins, jobname, config, copyfrom, user_opt, pass_opt):
    """Create jobs using config.xml or copy from another job"""

    user_opt, pass_opt = getCreds(ctx.obj['yaml_config_file'], jenkins, user_opt, pass_opt)

    if config is None and copyfrom is None:
        click.echo("Error: Atleast one of config.xml or copyfrom must be provided. Use --help flag to see all options.")
        click.echo("")
        exit(2)
    elif config is not None and copyfrom is not None:
        click.echo("Error: Ambiguous arguments: only one of --copyfrom <jobname> or --config <config.xml file path> is accepted.")

    try:
        j = jenkinssai.jenkins(jenkins, user_opt, pass_opt)
    except Exception as e:
        print "ERROR!!"
        print e.message
        click.echo("")
        exit(2)

    for name in jobname:
        try:
            job_url = j.create_job(name=name, configxmlfile=config.name, copyfrom=copyfrom)
            click.echo("=== Job %s" % name)
            click.echo("\tCreated job at %s" % job_url)
        except Exception as e:
            click.echo("=== Failed to create job %s" % name)
            print "\tError: ",
            print e.message
    click.echo("")

@jobs.command('config')
@click.pass_context
@click.argument('jobname', required=False)
@click.option('-J', '--jenkins', required=True, help="Jenkins URL or set environment variable JENKINS_URL", envvar="JENKINS_URL")
@click.option('-o', '--outfile', 'output_fp', type=click.File('wb'), help="path to config.xml file, default: ./config.xml", default="config.xml")
@click.option('-u', '--user', 'user_opt', envvar="JENKINS_USERNAME",
              help="Jenkins User Name or set the environment variable JENKINS_USERNAME")
@click.option('-p', '--password', 'pass_opt', envvar="JENKINS_PASSWORD",
              help="Jenkins Password or set the environment variable JENKINS_PASSWORD. We will prompt for password, if not supplied")
def config(ctx, jobname, jenkins, output_fp, user_opt, pass_opt):
    """Get config file for a job"""

    user_opt, pass_opt = getCreds(ctx.obj['yaml_config_file'], jenkins, user_opt, pass_opt)

    outfile = output_fp.name
    if not os.path.isabs(outfile):
        outfile = os.path.join(os.getcwd(), outfile)

    if jobname is None:
        parser_ = jenkins.split("/")
        jobname = parser_[-1]
        jenkins = "/".join(parser_[0:-1])

    click.echo("=== Job %s" % jobname)

    try:
        j = jenkinssai.jenkins(jenkins, user_opt, pass_opt)
        j.get_job_config_xml(jobname, outfile)
    except Exception as e:
        click.echo("\tError!!")
        print "\t",
        print e.message
        click.echo("")
        exit(2)

    click.echo("\tjob config saved to file "+outfile)
    click.echo("")

@jobs.command('disable-all')
@click.pass_context
@click.option('-J', '--jenkins', required=True, help="Jenkins URL or set environment variable JENKINS_URL", envvar="JENKINS_URL")
@click.option('-u', '--user', 'user_opt', envvar="JENKINS_USERNAME",
              help="Jenkins User Name or set the environment variable JENKINS_USERNAME")
@click.option('-p', '--password', 'pass_opt', envvar="JENKINS_PASSWORD",
              help="Jenkins Password or set the environment variable JENKINS_PASSWORD. We will prompt for password, if not supplied")
def disable_all(ctx, jenkins, user_opt, pass_opt):
    """Disable all jobs at a jenkins url"""

    user_opt, pass_opt = getCreds(ctx.obj['yaml_config_file'], jenkins, user_opt, pass_opt)

    try:
        j = jenkinssai.jenkins(jenkins, user_opt, pass_opt)
        j_jobs = j.get_jobs()

        if len(j_jobs) == 0:
            click.echo("No jobs to disable at %s" % jenkins)
            click.echo("")
            exit(0)
    except Exception as e:
        click.echo("ERROR: "+str(e.message))
        click.echo("")
        exit(2)

    click.echo("Following jobs on %s will be disabled:" % jenkins)
    click.echo('\n'.join(j_jobs))
    click.confirm('Do you want to continue?', abort=True)

    click.echo("Disabling all jobs at %s" % jenkins)
    click.echo("")
    for job in j_jobs:
        click.echo("=== Job: "+job)
        try:
            j.disable_job(job)
            click.echo("\t Successfully disabled.")
        except Exception as e:
            click.echo("\t "+str(e.message))
    click.echo("")

@jobs.command('enable-all')
@click.pass_context
@click.option('-J', '--jenkins', required=True, help="Jenkins URL or set environment variable JENKINS_URL", envvar="JENKINS_URL")
@click.option('-u', '--user', 'user_opt', envvar="JENKINS_USERNAME",
              help="Jenkins User Name or set the environment variable JENKINS_USERNAME")
@click.option('-p', '--password', 'pass_opt', envvar="JENKINS_PASSWORD",
              help="Jenkins Password or set the environment variable JENKINS_PASSWORD. We will prompt for password, if not supplied")
def enable_all(ctx, jenkins, user_opt, pass_opt):
    """Enable all jobs at a jenkins url"""

    user_opt, pass_opt = getCreds(ctx.obj['yaml_config_file'], jenkins, user_opt, pass_opt)

    try:
        j = jenkinssai.jenkins(jenkins, user_opt, pass_opt)
        j_jobs = j.get_jobs()

        if len(j_jobs) == 0:
            click.echo("No jobs to enable at %s" % jenkins)
            click.echo("")
            exit(0)
    except Exception as e:
        click.echo("ERROR: "+str(e.message))
        exit(2)

    for job in j_jobs:
        click.echo("=== Job: "+job)
        try:
            j.enable_job(job)
            click.echo("\t Successfully enabled.")
        except Exception as e:
            click.echo("\t "+str(e.message))
    click.echo("")

@jobs.command('delete-all')
@click.pass_context
@click.option('-J', '--jenkins', required=True, help="Jenkins URL or set environment variable JENKINS_URL", envvar="JENKINS_URL")
@click.option('-u', '--user', 'user_opt', envvar="JENKINS_USERNAME",
              help="Jenkins User Name or set the environment variable JENKINS_USERNAME")
@click.option('-p', '--password', 'pass_opt', envvar="JENKINS_PASSWORD",
              help="Jenkins Password or set the environment variable JENKINS_PASSWORD. We will prompt for password, if not supplied")
def delete_all(ctx, jenkins, user_opt, pass_opt):
    """Deletes all jobs under this url. This is irrecoverable. Use with caution."""

    user_opt, pass_opt = getCreds(ctx.obj['yaml_config_file'], jenkins, user_opt, pass_opt)

    try:
        j = jenkinssai.jenkins(jenkins, user_opt, pass_opt)
        j_jobs = j.get_jobs()

        if len(j_jobs) == 0:
            click.echo("No jobs to delete at %s" % jenkins)
            click.echo("")
            exit(0)
    except Exception as e:
        click.echo("ERROR: "+str(e.message))
        click.echo("")
        exit(2)

    click.echo("WARNING!!")
    click.echo("Destructive action. CAN NOT be reverted..")
    click.echo("Following jobs on %s will be deleted:" % jenkins)
    click.echo('\n'.join(j_jobs))
    click.confirm('Do you want to continue?', abort=True)

    for job in j_jobs:
        click.echo("=== Job: "+job)
        try:
            j.delete_job(job)
            click.echo("\t Successfully deleted.")
        except Exception as e:
            click.echo("\t "+str(e.message))
    click.echo("")

@basecli.command('plugin')
@click.pass_context
@click.option('-J', '--jenkins', required=True, help="Jenkins URL or set environment variable JENKINS_URL", envvar="JENKINS_URL")
@click.option('--noversions', is_flag=True, help="Do not show versions")
@click.option('-j', '--json', 'json_opt', is_flag=True, help="Output in JSON")
@click.option('-s', '--shell', 'shell_opt', is_flag=True, help="Shell friendly output")
@click.option('-u', '--user', 'user_opt', envvar="JENKINS_USERNAME",
              help="Jenkins User Name or set the environment variable JENKINS_USERNAME")
@click.option('-p', '--password', 'pass_opt', envvar="JENKINS_PASSWORD",
              help="Jenkins Password or set the environment variable JENKINS_PASSWORD. We will prompt for password, if not supplied")
def list(ctx, jenkins, noversions, json_opt, shell_opt, user_opt, pass_opt):
    """List installed plugins on the jenkins along with their versions"""

    user_opt, pass_opt = getCreds(ctx.obj['yaml_config_file'], jenkins, user_opt, pass_opt)

    if json_opt and shell_opt:
        click.echo("ERROR!!")
        click.echo("Ambiguous flags. shell and json flags can not be used together!!")
        click.echo("")
        exit(2)

    if not (shell_opt or json_opt):   click.echo("=== Installed Plugins in jenkins %s" % jenkins)
    try:
        j = jenkinssai.plugins(jenkins, user_opt, pass_opt)
        plugins = j.list_installed()
        if noversions:
            plugins = plugins.keys()

        if json_opt:
            print dumps(plugins, indent=4)
        elif shell_opt:
            if noversions:
                click.echo('\n'.join(plugins))
            else:
                for plugin, version in plugins.items():
                    click.echo("%s=%s" % (plugin, version))
        else:
            if noversions:
                print "\t",
                click.echo("\n\t".join(plugins))
            else:
                max_key_length = max(len(i) for i in plugins.keys())
                for plugin, version in plugins.items():
                    click.echo(plugin.ljust(max_key_length)+" : "+version)
    except Exception as e:
        click.echo("ERROR: "+str(e.message))
    click.echo("")

@basecli.command("migrate")
@click.pass_context
@click.option('-s', '--src', required=True, help="Source Jenkins URL")
@click.option('-d', '--dest', required=True, help="Destination Jenkins URL")
@click.option('-D', '--disable', help="Disable newly created jobs or the old jobs. Use src for source url or dest for desination url")
@click.option('--src-user', 'src_user_opt', help="Jenkins User Name for source jenkins url")
@click.option('--src-password', 'src_pass_opt', help="Jenkins Password for the source jenkins url. We will prompt for password, if not supplied")
@click.option('--dest-user', 'dest_user_opt', help="Jenkins User Name for destination jenkins url")
@click.option('--dest-password', 'dest_pass_opt', help="Jenkins Password for the destination jenkins url. We will prompt for password, if not supplied")
def migrate(ctx, src, dest, disable, src_user_opt, src_pass_opt, dest_user_opt, dest_pass_opt):
    """Copy jobs from one jenkins to another and optionally disable jobs on either source or destination jenkins"""

    if src_user_opt is not None and src_pass_opt is None:
        src_pass_opt = click.prompt("Enter Jenkins Password for user %s on jenkins %s" % (src_user_opt, src), type=str, hide_input=True)

    if dest_user_opt is not None and dest_pass_opt is None:
        dest_pass_opt = click.prompt("Enter Jenkins Password for user %s on jenkins %s" % (dest_user_opt, dest), type=str, hide_input=True)

    if disable is not None and disable.lower() != "src" and disable.lower() != "dest":
            click.echo("ERROR: Only 'src' or 'dest' values are allowed for 'disable' argument. Full jenkins urls are not allowed for safety.")
            click.echo("")
            exit(2)

    click.echo("=== Copying jobs from %s to %s" % (src, dest))
    try:
        src_j = jenkinssai.jenkins(src, src_user_opt, src_pass_opt)
        dest_j = jenkinssai.jenkins(dest, dest_user_opt, dest_pass_opt)

        dir_name = ".jenkinshelper_{0}".format(time.time())
        os.mkdir(dir_name)
    except Exception as e:
        click.echo("ERROR!!")
        click.echo(e.message)
        click.echo("")
        exit(2)

    for job in src_j.get_jobs():
        click.echo("    === %s" % job)
        try:
            config_file_ = "{0}/config_{1}.xml".format(dir_name, job)
            conf_file = src_j.get_job_config_xml(job, outputfile=config_file_)
            job_location = dest_j.create_job(job, configxmlfile=conf_file)
            click.echo("        %s" % job_location)
            if disable is not None:
                if disable.lower() == "src":
                    src_j.disable_job(job)
                    click.echo("        Job %s disabled on %s" % (job, src))
                elif disable.lower() == "dest":
                    dest_j.disable_job(job)
                    click.echo("        Job %s disabled on %s" % (job, dest))
        except Exception as e:
            print "    ERROR: ",
            print e.message

    if os.path.isdir(dir_name):
        for f in os.listdir(dir_name):
            os.remove(os.path.join(dir_name, f))
        os.rmdir(dir_name)
    click.echo("")

if __name__ == '__main__':
    basecli(obj={})
