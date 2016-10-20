import base64
import json
import os
import shutil
import sys
import tempfile
import zipfile

import docopt
import pkg_resources
import six

import dcoscli
from dcos import (cmds, config, cosmospackage, emitting, http, options,
                  package, subcommand, util)
from dcos.errors import DCOSException
from dcos.util import md5_hash_file
from dcoscli import tables
from dcoscli.subcommand import default_command_info, default_doc
from dcoscli.util import (decorate_docopt_usage, formatted_cli_version)

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
            hierarchy=['package', 'update'],
            arg_keys=[],
            function=_update),

        cmds.Command(
            hierarchy=['package', 'repo', 'list'],
            arg_keys=['--json'],
            function=_list_repos),

        cmds.Command(
            hierarchy=['package', 'repo', 'add'],
            arg_keys=['<repo-name>', '<repo-url>', '--index'],
            function=_add_repo),

        cmds.Command(
            hierarchy=['package', 'repo', 'remove'],
            arg_keys=['<repo-name>'],
            function=_remove_repo),

        cmds.Command(
            hierarchy=['package', 'build'],
            arg_keys=['<build-definition>', '--output-directory'],
            function=_build,
        ),
        cmds.Command(
            hierarchy=['package', 'describe'],
            arg_keys=['<package-name>', '--app', '--cli', '--options',
                      '--render', '--package-versions', '--package-version',
                      '--config'],
            function=_describe),

        cmds.Command(
            hierarchy=['package', 'install'],
            arg_keys=['<package-name>', '--package-version', '--options',
                      '--app-id', '--cli', '--app', '--yes'],
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
            arg_keys=['<package-name>', '--all', '--app-id', '--cli', '--app'],
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
        _info()
    else:
        doc = default_doc("package")
        emitter.publish(options.make_generic_usage_message(doc))
        return 1

    return 0


def _info():
    """Print package cli information.

    :returns: Process status
    :rtype: int
    """

    emitter.publish(default_command_info("package"))
    return 0


def _update():
    """
    :returns: Deprecation notice
    :rtype: str
    """

    _get_package_manager()
    notice = ("This command has been deprecated. "
              "Repositories will be automatically updated after they are added"
              " by `dcos package repo add`")
    raise DCOSException(notice)


def _list_repos(is_json):
    """List configured package repositories.

    :param is_json: output json if True
    :type is_json: bool
    :returns: Process status
    :rtype: int
    """

    package_manager = _get_package_manager()
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

    package_manager = _get_package_manager()
    package_manager.add_repo(repo_name, repo_url, index)

    return 0


def _remove_repo(repo_name):
    """Remove package repo and update repo with new repo

    :param repo_name: name to call repo
    :type repo_name: str
    :returns: Process status
    :rtype: int
    """

    package_manager = _get_package_manager()
    package_manager.remove_repo(repo_name)

    return 0


def _build(build_definition,
           output_directory):
    """ Creates a DC/OS Package from a DC/OS Package Build Definition

    :param build_definition: The path to a DC/OS Package Build Definition
    :type build_definition: str
    :param output_directory: The directory where the DC/OS Package
    will be stored
    :type output_directory: str
    :returns: The process status
    :rtype: int
    """
    # get the path of the build definition
    cwd = os.getcwd()
    build_definition_path = build_definition
    if not os.path.isabs(build_definition_path):
        build_definition_path = os.path.join(cwd, build_definition_path)

    build_definition_directory = os.path.dirname(build_definition_path)

    if not os.path.exists(build_definition_path):
        raise DCOSException(
            "The file [{}] does not exist".format(build_definition_path))

    # get the path to the output directory
    if output_directory is None:
        output_directory = cwd

    if not os.path.exists(output_directory):
        raise DCOSException(
            "The output directory [{}]"
            " does not exist".format(output_directory))

    logger.debug("Using [%s] as output directory", output_directory)

    # load raw build definition
    with util.open_file(build_definition_path) as bd:
        build_definition_raw = util.load_json(bd, keep_order=True)

    # validate DC/OS Package Build Definition with local references
    build_definition_schema_path = "data/schemas/build-definition-schema.json"
    build_definition_schema = util.load_jsons(
        pkg_resources.resource_string(
            "dcoscli", build_definition_schema_path).decode())

    errs = util.validate_json(build_definition_raw, build_definition_schema)

    if errs:
        logger.debug("Failed before resolution: \n"
                     "\tbuild definition: {}"
                     "".format(build_definition_raw))
        raise DCOSException(_validation_error(build_definition_path))

    # resolve local references in build definition
    _resolve_local_references(
        build_definition_raw,
        build_definition_schema,
        build_definition_directory
    )

    # at this point all the local references have been resolved
    build_definition_resolved = build_definition_raw

    # validate resolved build definition
    metadata_schema_path = "data/schemas/metadata-schema.json"
    metadata_schema = util.load_jsons(
        pkg_resources.resource_string(
            "dcoscli", metadata_schema_path).decode())

    errs = util.validate_json(build_definition_resolved, metadata_schema)

    if errs:
        logger.debug("Failed after resolution: \n"
                     "\tbuild definition: {}"
                     "".format(build_definition_resolved))
        raise DCOSException('Error validating package: '
                            'there was a problem resolving '
                            'the local references in '
                            '[{}]'.format(build_definition_path))

    # create the manifest
    manifest_json = {'built-by': formatted_cli_version()}

    # create the metadata
    metadata_json = build_definition_resolved

    # create zip file
    with tempfile.NamedTemporaryFile() as temp_file:
        with zipfile.ZipFile(
                temp_file.file,
                mode='w',
                compression=zipfile.ZIP_DEFLATED,
                allowZip64=True) as zip_file:

            metadata = json.dumps(metadata_json, indent=2).encode()
            zip_file.writestr("metadata.json", metadata)

            manifest = json.dumps(manifest_json, indent=2).encode()
            zip_file.writestr("manifest.json", manifest)

        # name the package appropriately
        temp_file.file.seek(0)
        dcos_package_name = '{}-{}-{}.dcos'.format(
            metadata_json['name'],
            metadata_json['version'],
            md5_hash_file(temp_file.file))

        # get the dcos package path
        dcos_package_path = os.path.join(output_directory, dcos_package_name)

        if os.path.exists(dcos_package_path):
            raise DCOSException(
                'Output file [{}] already exists'.format(
                    dcos_package_path))

        # create a new file to contain the package
        temp_file.file.seek(0)
        with util.open_file(dcos_package_path, 'w+b') as dcos_package:
            shutil.copyfileobj(temp_file.file, dcos_package)

    emitter.publish(
            'Created DCOS Universe package [{}].'.format(dcos_package_path))

    return 0


def _resolve_local_references(build_definition,
                              build_schema,
                              build_definition_directory):
    """ Resolves all local references in a DC/OS Package Build Definition

    :param build_definition: The DC/OS Package Build Definition that may
     contain local references
    :type build_definition: dict
    :param build_definition_directory: The directory of the Build Definition
    :type build_definition_directory: str
    :param build_schema: The schema for the Build Definition
    :type build_schema: dict
    """
    _replace_marathon(build_definition,
                      build_schema,
                      build_definition_directory)

    _replace_directly(build_definition,
                      build_schema,
                      build_definition_directory,
                      "config")

    _replace_directly(build_definition,
                      build_schema,
                      build_definition_directory,
                      "resource")


def _replace_directly(build_definition,
                      build_schema,
                      build_definition_directory,
                      ref):
    """ Replaces the local reference ref with the contents of
     the file pointed to by ref

    :param build_definition: The DC/OS Package Build Definition that
    may contain local references
    :type build_definition: dict
    :param build_definition_directory: The directory of the Build Definition
    :type build_definition_directory: str
    :param build_schema: The schema for the Build Definition
    :type build_schema: dict
    :param ref: The key in build_definition that will be replaced
    :type ref: str
    """
    if ref in build_definition and _is_local_reference(build_definition[ref]):
        location = build_definition[ref][1:]
        if not os.path.isabs(location):
            location = os.path.join(build_definition_directory, location)

        with util.open_file(location) as f:
            contents = util.load_json(f, True)

        build_definition[ref] = contents

        errs = util.validate_json(build_definition, build_schema)
        if errs:
            logger.debug("Failed during resolution of {}: \n"
                         "\tbuild definition: {}"
                         "".format(ref, build_definition))
            raise DCOSException(_validation_error(location))


def _replace_marathon(build_definition,
                      build_schema,
                      build_definition_directory):
    """ Replaces the marathon v2AppMustacheTemplate ref with
     the base64 encoding of the file pointed to by the reference

    :param build_definition: The DC/OS Package Build Definition that
     may contain local references
    :type build_definition: dict
    :param build_definition_directory: The directory of the Build Definition
    :type build_definition_directory: str
    :param build_schema: The schema for the Build Definition
    :type build_schema: dict
    """
    ref = "marathon"
    template = "v2AppMustacheTemplate"
    if ref in build_definition and \
            _is_local_reference(build_definition[ref][template]):
        location = (build_definition[ref])[template][1:]
        if not os.path.isabs(location):
            location = os.path.join(build_definition_directory, location)

        # convert the contents of the marathon file into base64
        with util.open_file(location) as f:
            contents = base64.b64encode(
                f.read().encode()).decode()

        build_definition[ref][template] = contents

        errs = util.validate_json(build_definition, build_schema)
        if errs:
            logger.debug("Failed during resolution of marathon: \n"
                         "\tbuild definition: {}"
                         "".format(build_definition))
            raise DCOSException(_validation_error(location))


def _validation_error(filename):
    """Renders a human readable validation error

    :param filename: the file that failed to validate
    :type filename: str
    :returns: validation error message
    :rtype: str
    """
    return 'Error validating package: ' \
           '[{}] does not conform to the' \
           ' specified schema'.format(filename)


def _is_local_reference(item):
    """Checks if an object is a local reference

    :param item: the object that may be a reference
    :type item: object
    :returns: true if item is a local reference else false
    :rtype: bool
    """
    return isinstance(item, six.string_types) and item.startswith("@")


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

    if package_versions and \
       (app or cli or options_path or render or package_version or config):
        raise DCOSException(
            'If --package-versions is provided, no other option can be '
            'provided')

    # If the user supplied template options, they definitely want to
    # render the template
    if options_path:
        render = True

    # Fail early if options file isn't valid
    user_options = _user_options(options_path)

    package_manager = _get_package_manager()
    pkg = package_manager.get_package_version(package_name, package_version)

    pkg_json = pkg.package_json()

    if package_versions:
        emitter.publish(pkg.package_versions())
    elif cli or app or config:
        if cli:
            emitter.publish(pkg.cli_definition())
        if app:
            if render:
                app_output = pkg.marathon_json(user_options)
            else:
                app_output = pkg.marathon_template()
                if app_output and app_output[-1] == '\n':
                    app_output = app_output[:-1]
            emitter.publish(app_output)
        if config:
            config_output = pkg.config_json()
            emitter.publish(config_output)
    else:
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
        # Expand ~ in the path
        path = os.path.expanduser(path)

        with util.open_file(path) as options_file:
            return util.load_json(options_file)


def confirm(prompt, yes):
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

    # Fail early if options file isn't valid
    user_options = _user_options(options_path)

    package_manager = _get_package_manager()
    pkg = package_manager.get_package_version(package_name, package_version)

    pkg_json = pkg.package_json()
    pre_install_notes = pkg_json.get('preInstallNotes')
    if app and pre_install_notes:
        emitter.publish(pre_install_notes)
        if not confirm('Continue installing?', yes):
            emitter.publish('Exiting installation.')
            return 0

    if app and pkg.has_mustache_definition():

        # Even though package installation will check for template rendering
        # errors, we want to fail early, before trying to install.
        pkg.options(user_options)

        # Install in Marathon
        msg = 'Installing Marathon app for package [{}] version [{}]'.format(
            pkg.name(), pkg.version())
        if app_id is not None:
            msg += ' with app id [{}]'.format(app_id)

        emitter.publish(msg)

        package_manager.install_app(pkg, user_options, app_id)

    if cli and pkg.has_cli_definition():
        # Install subcommand
        msg = 'Installing CLI subcommand for package [{}] version [{}]'.format(
            pkg.name(), pkg.version())
        emitter.publish(msg)

        subcommand.install(pkg)

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
    :type cli: bool
    :param package_name: The package to show
    :type package_name: str
    :returns: process return code
    :rtype: int
    """

    package_manager = _get_package_manager()
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

    package_manager = _get_package_manager()
    results = package_manager.search_sources(query)

    if json_ or results['packages']:
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

    package_manager = _get_package_manager()
    err = package.uninstall(
        package_manager, package_name, remove_all, app_id, cli, app)
    if err is not None:
        emitter.publish(err)
        return 1

    return 0


def get_cosmos_url():
    """
    :returns: cosmos base url
    :rtype: str
    """
    toml_config = config.get_config()
    cosmos_url = config.get_config_val("package.cosmos_url", toml_config)
    if cosmos_url is None:
        cosmos_url = config.get_config_val("core.dcos_url", toml_config)
        if cosmos_url is None:
            raise config.missing_config_exception(["core.dcos_url"])
    return cosmos_url


def _get_package_manager():
    """Returns type of package manager to use

    :returns: PackageManager instance
    :rtype: PackageManager
    """

    cosmos_url = get_cosmos_url()
    cosmos_manager = cosmospackage.Cosmos(cosmos_url)
    if cosmos_manager.enabled():
        return cosmos_manager
    else:
        msg = ("This version of the DC/OS CLI is not supported for your "
               "cluster. Please downgrade the CLI to an older version: "
               "https://dcos.io/docs/usage/cli/update/#downgrade"
               )
        raise DCOSException(msg)
