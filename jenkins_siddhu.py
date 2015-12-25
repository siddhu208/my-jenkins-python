from json import dumps
import click
import jenkinssai
import os
import time
from yaml import load as yaml_load, YAMLError
import codecs
from prettytable import PrettyTable

def __getJenkinsHostFromURL__(*urls):
    return [jenkins_url.split('http://')[-1].split('https://')[-1].split('www')[-1].split('/')[0].split(':')[0] for jenkins_url in urls]

def getCredsFromYaml(yaml_file, jenkins_url):

    try:
        with open(yaml_file) as f:
            conf = yaml_load(f)
            jenkins_host = __getJenkinsHostFromURL__(jenkins_url)[0]
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

def getCreds(yaml_file, jenkins_url, user_opt=None, pass_opt=None):

    if user_opt is not None and pass_opt is not None:
        return user_opt, pass_opt
    elif user_opt is not None and pass_opt is None:
        pass_opt = os.environ.get('JENKINS_PASSWORD', '')
        if pass_opt == '':
            pass_opt = click.prompt("Enter Password for user {0} on jenkins {1}".format(user_opt, jenkins_url), type=str, hide_input=True)
    elif user_opt is None and pass_opt is not None:
        click.echo("ERROR: Password is provided, but no username is found!!")
        click.echo("Check for environment variables if you have not provided the password via command line..")
        exit(2)
    elif user_opt is None and yaml_file is not None:
        user_opt, pass_opt = getCredsFromYaml(yaml_file, jenkins_url)
    else:
        user_opt, pass_opt = None, None
    return user_opt, pass_opt

def cleanup(dir_name):
    if os.path.isdir(dir_name):
        for f in os.listdir(dir_name):
            os.remove(os.path.join(dir_name, f))
        os.rmdir(dir_name)

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
def list_jobs(ctx, jenkins, json_opt, shell_opt, user_opt, pass_opt):
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
@click.argument('jobname')
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
@click.argument('jobnames', nargs=-1)
@click.option('-J', '--jenkins', required=True, help="Jenkins URL or set environment variable JENKINS_URL", envvar="JENKINS_URL")
@click.option('-u', '--user', 'user_opt', envvar="JENKINS_USERNAME",
              help="Jenkins User Name or set the environment variable JENKINS_USERNAME")
@click.option('-p', '--password', 'pass_opt', envvar="JENKINS_PASSWORD",
              help="Jenkins Password or set the environment variable JENKINS_PASSWORD. We will prompt for password, if not supplied")
def disable_all(ctx, jobnames, jenkins, user_opt, pass_opt):
    """Disable all jobs at a jenkins url.
    Disables job names that are passed as arguments. If no arguments are passed, all jobs under the jenkins url are disabled."""

    user_opt, pass_opt = getCreds(ctx.obj['yaml_config_file'], jenkins, user_opt, pass_opt)

    try:
        j = jenkinssai.jenkins(jenkins, user_opt, pass_opt)
        if not len(jobnames) == 0:
            j_jobs = jobnames
        else:
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
@click.argument('jobnames', nargs=-1)
@click.option('-J', '--jenkins', required=True, help="Jenkins URL or set environment variable JENKINS_URL", envvar="JENKINS_URL")
@click.option('-u', '--user', 'user_opt', envvar="JENKINS_USERNAME",
              help="Jenkins User Name or set the environment variable JENKINS_USERNAME")
@click.option('-p', '--password', 'pass_opt', envvar="JENKINS_PASSWORD",
              help="Jenkins Password or set the environment variable JENKINS_PASSWORD. We will prompt for password, if not supplied")
def enable_all(ctx, jobnames, jenkins, user_opt, pass_opt):
    """Enable all jobs at a jenkins url
    Enabes job names that are passed as arguments. If no arguments are passed, all jobs under the jenkins url are enabled."""

    user_opt, pass_opt = getCreds(ctx.obj['yaml_config_file'], jenkins, user_opt, pass_opt)

    try:
        j = jenkinssai.jenkins(jenkins, user_opt, pass_opt)
        if not len(jobnames) == 0:
            j_jobs = jobnames
        else:
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
@click.argument('jobnames', nargs=-1)
@click.option('-J', '--jenkins', required=True, help="Jenkins URL or set environment variable JENKINS_URL", envvar="JENKINS_URL")
@click.option('-u', '--user', 'user_opt', envvar="JENKINS_USERNAME",
              help="Jenkins User Name or set the environment variable JENKINS_USERNAME")
@click.option('-p', '--password', 'pass_opt', envvar="JENKINS_PASSWORD",
              help="Jenkins Password or set the environment variable JENKINS_PASSWORD. We will prompt for password, if not supplied")
def delete_all(ctx, jobnames, jenkins, user_opt, pass_opt):
    """Deletes all jobs under this url. This is irrecoverable. Use with caution.
    Deletes job names that are passed as arguments. If no arguments are passed, all jobs under the jenkins url are deleted."""

    user_opt, pass_opt = getCreds(ctx.obj['yaml_config_file'], jenkins, user_opt, pass_opt)

    try:
        j = jenkinssai.jenkins(jenkins, user_opt, pass_opt)
        if not len(jobnames) == 0:
            j_jobs = jobnames
        else:
            j_jobs = j.get_jobs()

        if len(j_jobs) == 0:
            click.echo("No jobs to delete at %s" % jenkins)
            click.echo("")
            exit(0)
    except Exception as e:
        click.echo("ERROR: "+str(e.message))
        click.echo("")
        exit(2)

    click.echo("\nWARNING!!")
    click.echo("Destructive action. CAN NOT be reverted..\n")
    click.echo("Following jobs on %s will be deleted:" % jenkins)
    click.echo('\t'+'\n\t'.join(j_jobs))
    click.confirm('Do you want to continue?', abort=True)

    for job in j_jobs:
        click.echo("=== Job: "+job)
        try:
            j.delete_job(job)
            click.echo("\t Successfully deleted.")
        except Exception as e:
            click.echo("\t "+str(e.message))
    click.echo("")

@basecli.command("migrate")
@click.pass_context
@click.option('-s', '--src', required=True, help="Source Jenkins URL")
@click.option('-d', '--dest', required=True, help="Destination Jenkins URL")
@click.option('-D', '--disable', help="Disable newly created jobs or the old jobs. Use src for source url or dest for desination url",
              type=click.Choice(['src', 'dest', 'all']))
@click.option('--src-user', 'src_user_opt', help="Jenkins User Name for source jenkins url")
@click.option('--src-password', 'src_pass_opt', help="Jenkins Password for the source jenkins url. We will prompt for password, if not supplied")
@click.option('--dest-user', 'dest_user_opt', help="Jenkins User Name for destination jenkins url")
@click.option('--dest-password', 'dest_pass_opt', help="Jenkins Password for the destination jenkins url. We will prompt for password, if not supplied")
def migrate(ctx, src, dest, disable, src_user_opt, src_pass_opt, dest_user_opt, dest_pass_opt):
    """Copy jobs from one jenkins to another and optionally disable jobs on either source or destination jenkins.
    Takes username and password from the yaml config file if provided or if JENKINS_CONFIG_YAML_FILE environment variable is set.
    see release-copy if you would like to move jobs in the same jenkins"""

    src_user_opt, src_pass_opt = getCreds(ctx.obj['yaml_config_file'], src, src_user_opt, src_pass_opt)
    dest_user_opt, dest_pass_opt = getCreds(ctx.obj['yaml_config_file'], dest, dest_user_opt, dest_pass_opt)

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
                if disable.lower() == "src" or disable.lower() == 'all':
                    src_j.disable_job(job)
                    click.echo("        Job %s disabled on %s" % (job, src))
                elif disable.lower() == "dest" or disable.lower() == 'all':
                    dest_j.disable_job(job)
                    click.echo("        Job %s disabled on %s" % (job, dest))
        except Exception as e:
            print "    ERROR: ",
            print e.message

    cleanup(dir_name)

@basecli.command('release-copy')
@click.pass_context
@click.option('-s', '--src', required=True, help="Source Jenkins URL (full url to the view)")
@click.option('-d', '--dest', required=True, help="Destination Jenkins URL (full url to the view)")
@click.option('-T', '--name-translate', 'job_name_translator', type=(str, str), multiple=False, required=True,
              help="Translation for job name, Format is <src> <dest>. All occurances of <src> will be replaced with <dest>. Make sure that the job name has the <src> string")
@click.option('-t', '--translate', 'translations', type=(str, str), multiple=True,
    help="Translation for new job. Format is <src> <dest>. All occurances of <src> will be replaced with <dest>. Make sure that the job name has the <src> string")
@click.option('-D', '--disable',
    help="Disable jobs. Disables jobs from source jenkins url if src, if dest disables jobs from dest url, if all, disables jobs from both src and dest jenkins urls",
    type=click.Choice(['src', 'dest', 'all']))
def release_copy(ctx, src, dest, job_name_translator, translations, disable):
    """Copy jobs from one view to another, may be from one jenkins to another also. As there can not be two jobs in the same view, translate parameters are needed.
    Two arguments are passed to option -T/--name-translate, like -T src dest; all occurances of src in the job name will be replaced
    with the value of dest and will be used as the new job name."""

    click.echo("=== Copying jobs from %s to %s" % (src, dest))

    src_user_opt, src_pass_opt = getCreds(ctx.obj['yaml_config_file'], src)
    dest_user_opt, dest_pass_opt = getCreds(ctx.obj['yaml_config_file'], dest)

    dir_name = str()
    done_flag = False

    try:
        src_j = jenkinssai.jenkins(src, src_user_opt, src_pass_opt)
        jobs_list = src_j.get_jobs()

        if len(jobs_list) == 0:
            click.echo("\tNo Jobs at %s" % src)
            done_flag = True
        elif not all([(job_name_translator[0] in x) for x in jobs_list]):
            ignore_jobs_list = [x for x in jobs_list if job_name_translator[0] not in x]
            jobs_list = [x for x in jobs_list if job_name_translator[0] in x]

            click.echo("\tFollowing Jobs do not have the string '%s' in them:" % job_name_translator[0])
            click.echo('\t'+'\n\t'.join(ignore_jobs_list))

            click.echo("\n\n")
            click.echo("\tOnly following Jobs will be copied to new jenkins:")
            click.echo('\t'+'\n\t'.join(jobs_list))
            if not click.confirm('Do you want to continue?'):
                click.echo('Aborting..')
                done_flag = True
    except Exception as e:
        click.echo("\tError: %s\n %s" % (e.message, '\n\n'.join([str(x) for x in e.args])))
        done_flag = True

    if done_flag:
        cleanup(dir_name)
        exit(2)

    try:
        dest_j = jenkinssai.jenkins(dest, dest_user_opt, dest_pass_opt)
        dir_name = ".jenkinshelper_{0}".format(time.time())
        os.mkdir(dir_name)
    except Exception as e:

        click.echo("\tERROR: %s\n %s" % (e.message, '\n\n'.join([str(x) for x in e.args])))
        cleanup(dir_name)
        exit(2)

    for job in jobs_list:
        click.echo("   === %s" % job)
        try:
            config_file_ = "{0}/config_{1}.xml".format(dir_name, job)
            conf_file = src_j.get_job_config_xml(job, outputfile=config_file_)

            ## Update the file with the tokens
            with codecs.open(conf_file, 'r', encoding='utf8') as in_file:
                content = in_file.read()

            for rep_values in translations:
                rep_values_new = [x.encode('utf8') for x in rep_values]
                content = content.replace(*rep_values_new)

            with codecs.open(conf_file, 'w', encoding='utf8') as out_file:
                out_file.write(content)

            new_job_name = job.replace(*job_name_translator)

            job_location = dest_j.create_job(new_job_name, configxmlfile=conf_file)

            click.echo("\tNew job: %s" % job_location)

            if disable is not None:
                if disable.lower() in ["src", "all"]:
                    src_j.disable_job(job)
                    click.echo("\tJob %s disabled on %s" % (job, src))
                elif disable.lower() in ["dest", "all"]:
                    dest_j.disable_job(new_job_name)
                    click.echo("\tJob %s disabled on %s" % (job, dest))

        except Exception as e:
            click.echo("\tERROR: %s\n %s" % (e.message, '\n\n'.join([str(x) for x in e.args])))

    cleanup(dir_name)
    click.echo('')


@basecli.group()
@click.pass_context
def plugins(ctx):
    """Manages Plugins"""

def __plugin_compares__(jenkinsurls=(), noversions=False, configFile=None):
    jenkins_hosts = dict()
    plugins_all = set()

    for jenkins_url in jenkinsurls:
        h = __getJenkinsHostFromURL__(jenkins_url)[0]

        if jenkins_hosts.has_key(h):
            continue

        jenkins_hosts[h] = dict()
        jenkins_hosts[h]['url'] = jenkins_url

        try:
            j = jenkinssai.plugins(jenkins_hosts[h]['url'],
                                   *getCreds(configFile, jenkins_url, user_opt=None, pass_opt=None))
            jenkins_hosts[h]['plugins'] = j.list_installed()
            plugins_all.update(jenkins_hosts[h]['plugins'].keys())
        except Exception as e:
            click.echo("ERROR: "+str(e.message))
            exit(2)

    output = dict()
    for plugin_ in plugins_all:
        output[plugin_] = dict()
        for host, pinfo in jenkins_hosts.items():
            output[plugin_][host] = dict()
            ## output[plugin_][host]['url'] = pinfo['url']
            output[plugin_][host]['exists'] = pinfo['plugins'].has_key(plugin_)

            if not noversions:
                if output[plugin_][host]['exists']:
                    output[plugin_][host]['plugin_version'] = pinfo['plugins'][plugin_]
                else:
                    output[plugin_][host]['plugin_version'] = "Not Found"

    return output

@plugins.command('list')
@click.pass_context
@click.option('-J', '--jenkins', required=True, help="Jenkins URL or set environment variable JENKINS_URL", envvar="JENKINS_URL")
@click.option('--names-only', 'noversions', is_flag=True, help="Do not show versions")
@click.option('-j', '--json', 'json_opt', is_flag=True, help="Output in JSON")
@click.option('-s', '--shell', 'shell_opt', is_flag=True, help="Shell friendly output")
@click.option('-u', '--user', 'user_opt', envvar="JENKINS_USERNAME",
              help="Jenkins User Name or set the environment variable JENKINS_USERNAME")
@click.option('-p', '--password', 'pass_opt', envvar="JENKINS_PASSWORD",
              help="Jenkins Password or set the environment variable JENKINS_PASSWORD. We will prompt for password, if not supplied")
def list_plugins(ctx, jenkins, noversions, json_opt, shell_opt, user_opt, pass_opt):
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

@plugins.command('compare')
@click.pass_context
@click.argument('jenkinsurls', nargs=-1, required=True)
@click.option('--names-only', 'noversions', is_flag=True, help="Do not show versions")
@click.option('-j', '--json', 'json_opt', is_flag=True, help="Output in JSON")
@click.option('-s', '--shell', 'shell_opt', is_flag=True, help="Shell friendly output")
@click.option('-p', '--pretty-print', 'pretty_print', is_flag=True,
              help="Pretty prints output. Because of the screen sizes, the output may not be as pretty as expected. Works well with two jenkins.")
def compare(ctx, jenkinsurls, noversions, json_opt, shell_opt, pretty_print):
    """List installed plugins on the jenkins along with their versions"""

    if len(jenkinsurls) < 2:
        click.echo("Atleast two jenkins URLs must be provided for comparison.")
        exit(2)

    if [json_opt, shell_opt, pretty_print].count(True) > 1:
        click.echo("ERROR!!")
        click.echo("Ambiguous flags. Only one of shell/json/pretty-print may be used!!")
        click.echo("")
        exit(2)

    plugins = __plugin_compares__(jenkinsurls, noversions, ctx.obj['yaml_config_file'])
    jenkins_hosts = __getJenkinsHostFromURL__(*jenkinsurls)

    if json_opt:
        click.echo(dumps(plugins, indent=4))
    elif shell_opt:
        for plugin_name, plugin_info in plugins.items():
            click.echo(plugin_name+":", nl=False)
            click.echo(';'.join(
                ["%s-->%s" % (host, (plugin_info[host]['exists']) if noversions else plugin_info[host]['plugin_version']) for host in jenkins_hosts]
                )
            )
    elif pretty_print:
        out_table = PrettyTable(['Plugin']+jenkins_hosts)
        out_table.align = 'l'

        for plugin_name, plugin_info in plugins.items():
            out_table.add_row([plugin_name]+[plugin_info[host]['exists'] if noversions else plugin_info[host]['plugin_version'] for host in jenkins_hosts])
        print out_table
    else:
        click.echo("Comparing plugins for ", nl=False)
        click.echo(' '.join(jenkins_hosts))
        for plugin_name, plugin_info in plugins.items():
            click.echo("=== %s:" % plugin_name)
            for host in jenkins_hosts:
                click.echo("\t%s: %s" % (host, (plugin_info[host]['exists']) if noversions else plugin_info[host]['plugin_version']))

    if not (shell_opt or json_opt):
        click.echo()

if __name__ == '__main__':
    basecli(obj={})
