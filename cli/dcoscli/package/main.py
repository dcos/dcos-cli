import json
import os

import docopt
import pkg_resources

import dcoscli
from dcos import cmds, emitting, http, options, package, subcommand, util
from dcos.errors import DCOSException
from dcos.package import get_package_manager
from dcoscli import tables
from dcoscli.subcommand import default_command_info, default_doc
from dcoscli.util import confirm, confirm_text, decorate_docopt_usage

logger = util.get_logger(__name__)

emitter = emitting.FlatEmitter()


def main(argv):
    try:
        return _main(argv)
    except DCOSException as e:
        emitter.publish(e)
        return 1


@decorate_docopt_usage
def _main(argv):
    args = docopt.docopt(
        default_doc("package"),
        argv=argv,
        version='dcos-package version {}'.format(dcoscli.version))
    http.silence_requests_warnings()

    return cmds.execute(_cmds(), args)


def _cmds():
    """
    :returns: All of the supported commands
    :rtype: dcos.cmds.Command
    """

    return [
        cmds.Command(
            hierarchy=['package', 'repo', 'list'],
            arg_keys=['--json'],
            function=_list_repos),

        cmds.Command(
            hierarchy=['package', 'repo', 'add'],
            arg_keys=['<repo-name>', '<repo-url>', '--index'],
            function=_add_repo),

        cmds.Command(
            hierarchy=['package', 'repo', 'import'],
            arg_keys=['<repos-file>'],
            function=_import_repos),

        cmds.Command(
            hierarchy=['package', 'repo', 'remove'],
            arg_keys=['<repo-names>'],
            function=_remove_repo),

        cmds.Command(
            hierarchy=['package', 'describe'],
            arg_keys=['<package-name>', '--app', '--cli', '--options',
                      '--render', '--package-versions', '--package-version',
                      '--config'],
            function=_describe),

        cmds.Command(
            hierarchy=['package', 'install'],
            arg_keys=['<package-name>', '--package-version', '--options',
                      '--app-id', '--cli', '--global', '--app', '--yes'],
            function=_install),

        cmds.Command(
            hierarchy=['package', 'list'],
            arg_keys=['--json', '--app-id', '--cli', '<package-name>'],
            function=_list),

        cmds.Command(
            hierarchy=['package', 'search'],
            arg_keys=['--json', '<query>'],
            function=_search),

        cmds.Command(
            hierarchy=['package', 'uninstall'],
            arg_keys=['<package-name>', '--all', '--app-id', '--cli', '--app',
                      '--yes'],
            function=_uninstall),

        cmds.Command(
            hierarchy=['package'],
            arg_keys=['--config-schema', '--info'],
            function=_package),
    ]


def _package(config_schema, info):
    """
    :param config_schema: Whether to output the config schema
    :type config_schema: boolean
    :param info: Whether to output a description of this subcommand
    :type info: boolean
    :returns: Process status
    :rtype: int
    """
    if config_schema:
        schema = json.loads(
            pkg_resources.resource_string(
                'dcos',
                'data/config-schema/package.json').decode('utf-8'))
        emitter.publish(schema)
    elif info:
        emitter.publish(default_command_info("package"))
    else:
        doc = default_doc("package")
        emitter.publish(options.make_generic_usage_message(doc))
        return 1

    return 0


def _list_repos(is_json):
    """List configured package repositories.

    :param is_json: output json if True
    :type is_json: bool
    :returns: Process status
    :rtype: int
    """

    package_manager = get_package_manager()
    repos = package_manager.get_repos()

    if is_json:
        return emitter.publish(repos)
    elif repos.get("repositories"):
        repos = ["{}: {}".format(repo.get("name"), repo.get("uri"))
                 for repo in repos.get("repositories")]
        emitter.publish("\n".join(repos))
    else:
        msg = ("There are currently no repos configured. "
               "Please use `dcos package repo add` to add a repo")
        raise DCOSException(msg)

    return 0


def _add_repo(repo_name, repo_url, index):
    """Add package repo and update repo with new repo

    :param repo_name: name to call repo
    :type repo_name: str
    :param repo_url: location of repo to add
    :type repo_url: str
    :param index: index to add this repo
    :type index: int
    :rtype: None
    """

    package_manager = get_package_manager()
    package_manager.add_repo(repo_name, repo_url, index)

    return 0


def _import_repos(repos_file):
    """Add package repos from a JSON file

    :param repos_file: path to JSON file containing repos.
    :type repos_file: str
    :rtype: int
    """

    package_manager = get_package_manager()

    with open(repos_file) as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            _raise_invalid_repos_file()
        repositories = data.get('repositories')
        if not repositories:
            _raise_invalid_repos_file()

        for index, repo in enumerate(data['repositories']):
            repo_name = repo.get('name')
            repo_uri = repo.get('uri')
            if not repo_name or not repo_uri:
                emitter.publish('Repo missing name or uri. Skipping.')
                continue
            try:
                package_manager.add_repo(repo['name'], repo['uri'], index)
                emitter.publish('Added repo "%s" (%s) at index %d'
                                % (repo_name, repo_uri, index))
            except DCOSException as e:
                emitter.publish('Error (%s) while adding repo "%s" (%s). '
                                'Skipping.'
                                % (e, repo_name, repo_uri))
                continue

    return 0


def _raise_invalid_repos_file():
    raise DCOSException(
        'No repositories found to import. '
        'You should provide a file containing package '
        'repositories, listed in the format of `dcos package list --json`.'
        '\nExample: '
        '{"repositories": [{"name": "Universe", "uri": "uri-here"}]}')


def _remove_repo(repo_names):
    """Remove package repo and update repo with new repo

    :param repo_names: names of repos
    :type repo_name: [str]
    :returns: Process status
    :rtype: int
    """

    package_manager = get_package_manager()
    for repo_name in repo_names:
        package_manager.remove_repo(repo_name)

    return 0


def _describe(package_name,
              app,
              cli,
              options_path,
              render,
              package_versions,
              package_version,
              config):
    """Describe the specified package.

    :param package_name: The package to describe
    :type package_name: str
    :param app: If True, marathon.json will be printed
    :type app: boolean
    :param cli: If True, command.json | resource.json's cli property should
                be printed
    :type cli: boolean
    :param options_path: Path to json file with options to override
                         config.json defaults.
    :type options_path: str
    :param render: If True, marathon.json will be rendered
    :type render: boolean
    :param package_versions: If True, a list of all package versions will
                             be printed
    :type package_versions: boolean
    :param package_version: package version
    :type package_version: str | None
    :param config: If True, config.json will be printed
    :type config: boolean
    :returns: Process status
    :rtype: int
    """

    # If the user supplied template options, they definitely want to
    # render the template
    if options_path:
        render = True

    # Fail early if options file isn't valid
    user_options = util.read_file_json(options_path)

    package_manager = get_package_manager()
    pkg = package_manager.get_package_version(package_name, package_version)

    if package_versions:
        emitter.publish(pkg.package_versions())
    elif cli or app or config:
        if cli:
            emitter.publish(pkg.cli_definition())
        if app:
            if render:
                app_output = pkg.marathon_json(user_options)
            else:
                app_output = pkg.marathon_template().decode("UTF-8")
                if app_output and app_output[-1] == '\n':
                    app_output = app_output[:-1]
            emitter.publish(app_output)
        if config:
            config_output = pkg.config_json()
            emitter.publish(config_output)
    else:
        emitter.publish(pkg.package_response())

    return 0


def _install(package_name, package_version, options_path, app_id, cli,
             global_, app, yes):
    """Install the specified package.

    :param package_name: the package to install
    :type package_name: str
    :param package_version: package version to install
    :type package_version: str
    :param options_path: path to file containing option values
    :type options_path: str
    :param app_id: app ID for installation of this package
    :type app_id: str
    :param cli: indicates if the cli should be installed
    :type cli: bool
    :param global_: indicates that the cli should be installed globally
    :type global_: bool
    :param app: indicate if the application should be installed
    :type app: bool
    :param yes: automatically assume yes to all prompts
    :type yes: bool
    :returns: process status
    :rtype: int
    """

    if cli is False and app is False:
        # Install both if neither flag is specified
        cli = app = True

    # Fail early if options file isn't valid
    user_options = util.read_file_json(options_path)

    package_manager = get_package_manager()
    pkg = package_manager.get_package_version(package_name, package_version)

    pkg_json = pkg.package_json()

    selected = pkg_json.get('selected')
    if selected:
        link = ('https://mesosphere.com/'
                'catalog-terms-conditions/#certified-services')
    else:
        link = ('https://mesosphere.com/'
                'catalog-terms-conditions/#community-services')
    emitter.publish(
        ('By Deploying, you agree to '
         'the Terms and Conditions ' + link)
    )

    pre_install_notes = pkg_json.get('preInstallNotes')
    if app and pre_install_notes:
        emitter.publish(pre_install_notes)

    if not confirm('Continue installing?', yes):
        emitter.publish('Exiting installation.')
        return 1

    if app and pkg.marathon_template():

        # Even though package installation will check for template rendering
        # errors, we want to fail early, before trying to install.
        pkg.options(user_options)

        # Install in Marathon
        msg = 'Installing Marathon app for package [{}] version [{}]'.format(
            pkg.name(), pkg.version())
        if app_id is not None:
            msg += ' with app id [{}]'.format(app_id)

        emitter.publish(msg)

        if app_id is not None:
            msg = "Usage of --app-id is deprecated. Use --options instead " \
                  "and specify a file that contains [service.name] property"
            emitter.publish(msg)

        package_manager.install_app(pkg, user_options, app_id)

    if cli and pkg.cli_definition():
        # Install subcommand
        msg = 'Installing CLI subcommand for package [{}] version [{}]'.format(
            pkg.name(), pkg.version())
        emitter.publish(msg)

        subcommand.install(pkg, global_)

        subcommand_paths = subcommand.get_package_commands(package_name)
        new_commands = [os.path.basename(p).replace('-', ' ', 1)
                        for p in subcommand_paths]

        if new_commands:
            commands = ', '.join(new_commands)
            plural = "s" if len(new_commands) > 1 else ""
            emitter.publish("New command{} available: {}".format(plural,
                                                                 commands))

    post_install_notes = pkg_json.get('postInstallNotes')
    if app and post_install_notes:
        emitter.publish(post_install_notes)

    return 0


def _list(json_, app_id, cli_only, package_name):
    """List installed apps

    :param json_: output json if True
    :type json_: bool
    :param app_id: App ID of app to show
    :type app_id: str
    :param cli_only: if True, only show packages with installed subcommands
    :type cli_only: bool
    :param package_name: The package to show
    :type package_name: str
    :returns: process return code
    :rtype: int
    """

    package_manager = get_package_manager()
    if app_id is not None:
        app_id = util.normalize_marathon_id_path(app_id)
    results = package.installed_packages(
        package_manager, app_id, package_name, cli_only)

    # only emit those packages that match the provided package_name and app_id
    if results or json_:
        emitting.publish_table(emitter, results, tables.package_table, json_)
    else:
        msg = ("There are currently no installed packages. "
               "Please use `dcos package install` to install a package.")
        raise DCOSException(msg)
    return 0


def _matches_package_name(name, pkg_info):
    """
    :param name: the name of the package
    :type name: str
    :param pkg_info: the package description
    :type pkg_info: dict
    :returns: True if the name is not defined or the package matches that name;
              False otherwise
    :rtype: bool
    """

    return name is None or pkg_info['name'] == name


def _matches_app_id(app_id, pkg_info):
    """
    :param app_id: the application id
    :type app_id: str
    :param pkg_info: the package description
    :type pkg_info: dict
    :returns: True if the app id is not defined or the package matches that app
              id; False otherwize
    :rtype: bool
    """

    return app_id is None or app_id in pkg_info.get('apps')


def _search(json_, query):
    """Search for matching packages.

    :param json_: output json if True
    :type json_: bool
    :param query: The search term
    :type query: str
    :returns: Process status
    :rtype: int
    """

    if not query:
        query = ''

    package_manager = get_package_manager()
    results = package_manager.search_sources(query)

    if json_ or results['packages']:
        emitting.publish_table(emitter,
                               results,
                               tables.package_search_table,
                               json_)
    else:
        raise DCOSException('No packages found.')
    return 0


def _uninstall(package_name, remove_all, app_id, cli, app, skip_confirmation):
    """Uninstall the specified package.

    :param package_name: The package to uninstall
    :type package_name: str
    :param remove_all: Whether to remove all instances of the named package
    :type remove_all: boolean
    :param app_id: App ID of the package instance to uninstall
    :type app_id: str
    :param skip_confirmation: Skip confirmation for uninstall
    :type skip_confirmation: boolean
    :returns: Process status
    :rtype: int
    """

    # Don't gate CLI uninstalls.
    # Don't gate uninstalls if the user wants to skip confirmation.
    if not cli and not skip_confirmation and not _confirm_uninstall(
        package_name,
        remove_all,
        app_id
    ):
        return 0

    package_manager = get_package_manager()
    package.uninstall(
        package_manager, package_name, remove_all, app_id, cli, app)

    return 0


def _confirm_uninstall(package_name, remove_all, app_id):
    """Interactively confirm the uninstall with the user.

    :param package_name: The package to uninstall
    :type package_name: str
    :param remove_all: Whether to remove all instances of the named package
    :type remove_all: boolean
    :param app_id: App ID of the package instance to uninstall
    :type app_id: str
    :returns: Whether the uninstall should proceeed or not.
    :rtype: bool
    """

    if remove_all:
        confirm_cta = ("WARNING: This action cannot be undone. This will "
                       "uninstall all instances of the [{package_name}] "
                       "package, and delete all data for all {package_name} "
                       "instances.").format(package_name=package_name)
        confirm_prompt = "Please type 'uninstall all {}'".format(package_name)
        expected_text = "uninstall all {}".format(package_name)
    elif app_id:
        confirm_cta = ("WARNING: This action cannot be undone. This will "
                       "uninstall [{}] and delete all of its persistent "
                       "(logs, configurations, database artifacts, "
                       "everything).").format(app_id)
        confirm_prompt = "Please type the name of the service to confirm"
        expected_text = app_id
    else:
        confirm_cta = ("WARNING: This action cannot be undone. This will "
                       "uninstall [{}] and delete all of its persistent "
                       "data (logs, configurations, database artifacts, "
                       "everything).").format(package_name)
        confirm_prompt = "Please type the name of the service to confirm"
        expected_text = package_name

    emitter.publish(confirm_cta)
    if not confirm_text(confirm_prompt, expected_text):
        emitter.publish("Cancelling uninstall.")
        return False
    else:
        return True
