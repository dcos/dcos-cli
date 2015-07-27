import json
import os
import sys

import dcoscli
import docopt
import pkg_resources
from dcos import (cmds, emitting, http, marathon, options, package, subcommand,
                  util)
from dcos.errors import DCOSException
from dcoscli import tables

logger = util.get_logger(__name__)
emitter = emitting.FlatEmitter()


def main():
    try:
        return _main()
    except DCOSException as e:
        emitter.publish(e)
        return 1


def _doc():
    return pkg_resources.resource_string(
        'dcoscli',
        'data/help/package.txt').decode('utf-8')


def _main():
    util.configure_process_from_environ()

    args = docopt.docopt(
        _doc(),
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
            hierarchy=['package', 'sources'],
            arg_keys=[],
            function=_list_sources),

        cmds.Command(
            hierarchy=['package', 'update'],
            arg_keys=['--validate'],
            function=_update),

        cmds.Command(
            hierarchy=['package', 'describe'],
            arg_keys=['<package_name>', '--cli', '--app', '--options'],
            function=_describe),

        cmds.Command(
            hierarchy=['package', 'install'],
            arg_keys=['<package_name>', '--package-version', '--options',
                      '--app-id', '--cli', '--app', '--yes'],
            function=_install),

        cmds.Command(
            hierarchy=['package', 'list'],
            arg_keys=['--json', '--endpoints', '--app-id', '<package_name>'],
            function=_list),

        cmds.Command(
            hierarchy=['package', 'search'],
            arg_keys=['--json', '<query>'],
            function=_search),

        cmds.Command(
            hierarchy=['package', 'uninstall'],
            arg_keys=['<package_name>', '--all', '--app-id', '--cli', '--app'],
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
                'dcoscli',
                'data/config-schema/package.json').decode('utf-8'))
        emitter.publish(schema)
    elif info:
        _info()
    else:
        emitter.publish(options.make_generic_usage_message(_doc()))
        return 1

    return 0


def _info():
    """Print package cli information.

    :returns: Process status
    :rtype: int
    """

    emitter.publish(_doc().split('\n')[0])
    return 0


def _list_sources():
    """List configured package sources.

    :returns: Process status
    :rtype: int
    """

    config = util.get_config()

    sources = package.list_sources(config)

    for source in sources:
        emitter.publish("{} {}".format(source.hash(), source.url))

    return 0


def _update(validate):
    """Update local package definitions from sources.

    :param validate: Whether to validate package content when updating sources.
    :type validate: bool
    :returns: Process status
    :rtype: int
    """

    config = util.get_config()

    package.update_sources(config, validate)

    return 0


def _describe(package_name, cli, app, options_path):
    """Describe the specified package.

    :param package_name: The package to describe
    :type package_name: str
    :returns: Process status
    :rtype: int
    """

    config = util.get_config()

    pkg = package.resolve_package(package_name, config)

    if pkg is None:
        raise DCOSException("Package [{}] not found".format(package_name))

    # TODO(CD): Make package version to describe configurable
    pkg_revision = pkg.latest_package_revision()
    pkg_json = pkg.package_json(pkg_revision)
    revision_map = pkg.package_revisions_map()
    pkg_versions = list(revision_map.values())

    del pkg_json['version']
    pkg_json['versions'] = pkg_versions

    if cli or app:
        user_options = _user_options(options_path)
        options = pkg.options(pkg_revision, user_options)

        if cli:
            pkg_json['command'] = pkg.command_json(pkg_revision, options)
        if app:
            pkg_json['app'] = pkg.marathon_json(pkg_revision, options)

    emitter.publish(pkg_json)
    return 0


def _user_options(path):
    """ Read the options at the given file path.

    :param path: file path
    :type path: str
    :returns: options
    :rtype: dict
    """
    if path is None:
        return {}
    else:
        with util.open_file(path) as options_file:
            return util.load_json(options_file)


def _confirm(prompt, yes):
    """
    :param prompt: message to display to the terminal
    :type prompt: str
    :param yes: whether to assume that the user responded with yes
    :type yes: bool
    :returns: True if the user responded with yes; False otherwise
    :rtype: bool
    """

    if yes:
        return True
    else:
        while True:
            sys.stdout.write('{} [yes/no] '.format(prompt))
            sys.stdout.flush()
            response = sys.stdin.readline().strip().lower()
            if response == 'yes' or response == 'y':
                return True
            elif response == 'no' or response == 'n':
                return False
            else:
                emitter.publish(
                    "'{}' is not a valid response.".format(response))


def _install(package_name, package_version, options_path, app_id, cli, app,
             yes):
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

    config = util.get_config()

    pkg = package.resolve_package(package_name, config)
    if pkg is None:
        msg = "Package [{}] not found\n".format(package_name) + \
              "You may need to run 'dcos package update' to update your " + \
              "repositories"
        raise DCOSException(msg)

    pkg_revision = pkg.latest_package_revision(package_version)
    if pkg_revision is None:
        msg = "Package [{}] not available".format(package_name)
        if package_version is not None:
            msg += " with version {}".format(package_version)
        raise DCOSException(msg)

    pkg_json = pkg.package_json(pkg_revision)
    pre_install_notes = pkg_json.get('preInstallNotes')
    if pre_install_notes:
        emitter.publish(pre_install_notes)
        if not _confirm('Continue installing?', yes):
            emitter.publish('Exiting installation.')
            return 0

    user_options = _user_options(options_path)

    options = pkg.options(pkg_revision, user_options)

    revision_map = pkg.package_revisions_map()
    package_version = revision_map.get(pkg_revision)

    if app and pkg.has_marathon_definition(pkg_revision):
        # Install in Marathon
        msg = 'Installing Marathon app for package [{}] version [{}]'.format(
            pkg.name(), package_version)
        if app_id is not None:
            msg += ' with app id [{}]'.format(app_id)

        emitter.publish(msg)

        init_client = marathon.create_client(config)

        package.install_app(
            pkg,
            pkg_revision,
            init_client,
            options,
            app_id)

    if cli and pkg.has_command_definition(pkg_revision):
        # Install subcommand
        msg = 'Installing CLI subcommand for package [{}] version [{}]'.format(
            pkg.name(), package_version)
        emitter.publish(msg)

        subcommand.install(pkg, pkg_revision, options)

        subcommand_paths = subcommand.get_package_commands(package_name)
        new_commands = [os.path.basename(p).replace('-', ' ', 1)
                        for p in subcommand_paths]

        if new_commands:
            commands = ', '.join(new_commands)
            plural = "s" if len(new_commands) > 1 else ""
            emitter.publish("New command{} available: {}".format(plural,
                                                                 commands))

    post_install_notes = pkg_json.get('postInstallNotes')
    if post_install_notes:
        emitter.publish(post_install_notes)

    return 0


def _list(json_, endpoints, app_id, package_name):
    """List installed apps

    :param json_: output json if True
    :type json_: bool
    :param endpoints: Whether to include a list of
        endpoints as port-host pairs
    :type endpoints: boolean
    :param app_id: App ID of app to show
    :type app_id: str
    :param package_name: The package to show
    :type package_name: str
    :returns: process return code
    :rtype: int
    """

    config = util.get_config()
    init_client = marathon.create_client(config)
    installed = package.installed_packages(init_client, endpoints)

    # only emit those packages that match the provided package_name and app_id
    results = []
    for pkg in installed:
        pkg_info = pkg.dict()
        if (_matches_package_name(package_name, pkg_info) and
                _matches_app_id(app_id, pkg_info)):
            if app_id:
                # if the user is asking a specific id then only show that id
                pkg_info['apps'] = [
                    app for app in pkg_info['apps']
                    if app == app_id
                ]

            results.append(pkg_info)

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

    config = util.get_config()
    results = [index_entry.as_dict()
               for index_entry in package.search(query, config)]

    if any(result['packages'] for result in results) or json_:
        emitting.publish_table(emitter,
                               results,
                               tables.package_search_table,
                               json_)
    else:
        raise DCOSException('No packages found.')
    return 0


def _uninstall(package_name, remove_all, app_id, cli, app):
    """Uninstall the specified package.

    :param package_name: The package to uninstall
    :type package_name: str
    :param remove_all: Whether to remove all instances of the named package
    :type remove_all: boolean
    :param app_id: App ID of the package instance to uninstall
    :type app_id: str
    :returns: Process status
    :rtype: int
    """

    err = package.uninstall(package_name, remove_all, app_id, cli, app)
    if err is not None:
        emitter.publish(err)
        return 1

    return 0
