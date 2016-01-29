import abc
import base64
import collections
import copy
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import zipfile
from distutils.version import LooseVersion

import git
import portalocker
import pystache
import six
from dcos import (constants, emitting, errors, http, marathon, mesos,
                  subcommand, util)
from dcos.errors import DCOSException, DefaultError

from six.moves import urllib

logger = util.get_logger(__name__)

emitter = emitting.FlatEmitter()


PACKAGE_METADATA_KEY = 'DCOS_PACKAGE_METADATA'
PACKAGE_NAME_KEY = 'DCOS_PACKAGE_NAME'
PACKAGE_VERSION_KEY = 'DCOS_PACKAGE_VERSION'
PACKAGE_SOURCE_KEY = 'DCOS_PACKAGE_SOURCE'
PACKAGE_FRAMEWORK_KEY = 'DCOS_PACKAGE_IS_FRAMEWORK'
PACKAGE_RELEASE_KEY = 'DCOS_PACKAGE_RELEASE'
PACKAGE_COMMAND_KEY = 'DCOS_PACKAGE_COMMAND'
PACKAGE_REGISTRY_VERSION_KEY = 'DCOS_PACKAGE_REGISTRY_VERSION'
PACKAGE_FRAMEWORK_NAME_KEY = 'DCOS_PACKAGE_FRAMEWORK_NAME'


def _find_framework_name(package_name, options):
    """
    :param package_name: the name of the package
    :type package_name: str
    :param options: the options object
    :type options: dict
    :returns: the name of framework if found; None otherwise
    :rtype: str
    """

    return options.get(package_name, {}).get('framework-name', None)


def _base64_encode(dictionary):
    """Returns base64(json(dictionary)).

    :param dictionary: dict to encode
    :type dictionary: dict
    :returns: base64 encoding
    :rtype: str
    """

    json_str = json.dumps(dictionary, sort_keys=True)
    str_bytes = six.b(json_str)
    return base64.b64encode(str_bytes).decode('utf-8')


def uninstall(pkg, package_name, remove_all, app_id, cli, app):
    """Uninstalls a package.

    :param pkg: package manager to uninstall with
    :type pkg: PackageManager
    :param package_name: The package to uninstall
    :type package_name: str
    :param remove_all: Whether to remove all instances of the named app
    :type remove_all: boolean
    :param app_id: App ID of the app instance to uninstall
    :type app_id: str
    :param init_client: The program to use to run the app
    :type init_client: object
    :rtype: None
    """

    if cli is False and app is False:
        cli = app = True

    uninstalled = False
    if cli:
        if subcommand.uninstall(package_name):
            uninstalled = True

    if app:
        if pkg.uninstall_app(package_name, remove_all, app_id):
            uninstalled = True

    if uninstalled:
        return None
    else:
        msg = 'Package [{}]'.format(package_name)
        if app_id is not None:
            msg += " with id [{}]".format(app_id)
        msg += " is not installed."
        raise DCOSException(msg)


def uninstall_subcommand(distribution_name):
    """Uninstalls a subcommand.

    :param distribution_name: the name of the package
    :type distribution_name: str
    :returns: True if the subcommand was uninstalled
    :rtype: bool
    """

    return subcommand.uninstall(distribution_name)


class InstalledPackage(object):
    """Represents an intalled DCOS package.  One of `app` and
    `subcommand` must be supplied.

    :param apps: A dictionary representing a marathon app. Of the
                format returned by `installed_apps()`
    :type apps: [dict]
    :param subcommand: Installed subcommand
    :type subcommand: subcommand.InstalledSubcommand
    """

    def __init__(self, apps=[], subcommand=None):
        assert apps or subcommand
        self.apps = apps
        self.subcommand = subcommand

    def name(self):
        """
        :returns: The name of the package
        :rtype: str
        """
        if self.subcommand:
            return self.subcommand.name
        else:
            return self.apps[0]['name']

    def dict(self):
        """ A dictionary representation of the package.  Used by `dcos package
        list`.

        :returns: A dictionary representation of the package.
        :rtype: dict
        """
        ret = {}

        if self.subcommand:
            ret['command'] = {'name': self.subcommand.name}

        if self.apps:
            ret['apps'] = sorted([app['appId'] for app in self.apps])

        if self.subcommand:
            package_json = self.subcommand.package_json()
            ret.update(package_json)

            ret['packageSource'] = self.subcommand.package_source()
            ret['releaseVersion'] = self.subcommand.package_revision()
        else:
            ret.update(self.apps[0])
            ret.pop('appId')

        return ret


def installed_packages(package_manager, endpoints):
    """Returns all installed packages in the format:

    [{
       'apps': [<id>],
       'command': {
         'name': <name>
       }
       ...<metadata>...
    }]

    :param init_client: The program to use to list packages
    :type init_client: object
    :param endpoints: Whether to include a list of
                      endpoints as port-host pairs
    :type endpoints: boolean
    :returns: A list of installed packages
    :rtype: [InstalledPackage]
    """

    # TODO: make sure that endpoints works
    apps = package_manager.installed_apps(None, None)
    subcommands = installed_subcommands()

    dicts = collections.defaultdict(lambda: {'apps': [], 'command': None})

    for app in apps:
        key = (app['name'], app['releaseVersion'], app['packageSource'])
        dicts[key]['apps'].append(app)

    for subcmd in subcommands:
        package_revision = subcmd.package_revision()
        package_source = subcmd.package_source()
        key = (subcmd.name, package_revision, package_source)
        dicts[key]['command'] = subcmd

    return [
        InstalledPackage(pkg['apps'], pkg['command']) for pkg in dicts.values()
    ]


def installed_subcommands():
    """Returns all installed subcommands.

    :returns: all installed subcommands
    :rtype: [InstalledSubcommand]
    """

    return [subcommand.InstalledSubcommand(name) for name in
            subcommand.distributions()]


def _decode_and_add_context(app_id, labels):
    """ Create an enhanced package JSON from Marathon labels

    {
      'appId': <appId>,
      'packageSource': <source>,
      'releaseVersion': <release_version>,
      ..<package.json properties>..
    }

    :param app_id: Marathon application id
    :type app_id: str
    :param labels: Marathon label dictionary
    :type labels: dict
    :rtype: dict
    """

    # TODO: remove images if it exists

    encoded = labels.get(PACKAGE_METADATA_KEY, {})
    decoded = base64.b64decode(six.b(encoded)).decode()

    decoded_json = util.load_jsons(decoded)
    decoded_json['appId'] = app_id
    decoded_json['packageSource'] = labels.get(PACKAGE_SOURCE_KEY)
    decoded_json['releaseVersion'] = labels.get(PACKAGE_RELEASE_KEY)

    return decoded_json


def search(query, cfg):
    """Returns a list of index entry collections, one for each registry in
    the supplied config.

    :param query: The search term
    :type query: str
    :param cfg: Configuration dictionary
    :type cfg: dcos.config.Toml
    :rtype: [IndexEntries]
    """

    threshold = 0.5  # Minimum rank required to appear in results
    results = []

    def clean_package_entry(entry):
        result = entry.copy()
        result.update({
            'versions': list(entry['versions'].keys())
        })
        return result

    for registry in registries(cfg):
        source_results = []
        index = registry.get_index()

        for pkg in index['packages']:
            rank = _search_rank(pkg, query)
            if rank >= threshold:
                source_results.append(clean_package_entry(pkg))

        entries = IndexEntries(registry.source, source_results)
        results.append(entries)

    return results


def _search_rank(pkg, query):
    """
    :param pkg: Index entry to rank for affinity with the search term
    :type pkg: object
    :param query: Search term
    :type query: str
    :rtype: float
    """
    result = 0.0

    wildcard_symbol = '*'
    regex_pattern = '.*'

    q = query.lower()
    if wildcard_symbol in q:
        q = q.replace(wildcard_symbol, regex_pattern)
        if q.endswith(wildcard_symbol):
            q = '^{}'.format(q)
        else:
            q = '{}$'.format(q)

        if re.match(q, pkg['name'].lower()):
            result += 2.0
        return result

    if q in pkg['name'].lower():
        result += 2.0
    for tag in pkg['tags']:
        if q in tag.lower():
            result += 1.0

    if q in pkg['description'].lower():
        result += 0.5

    return result


def _extract_default_values(config_schema):
    """
    :param config_schema: A json-schema describing configuration options.
    :type config_schema: dict
    :returns: a dictionary with the default specified by the schema
    :rtype: dict | None
    """

    defaults = {}
    if 'properties' not in config_schema:
        return None

    for key, value in config_schema['properties'].items():
        if isinstance(value, dict) and 'default' in value:
            defaults[key] = value['default']
        elif isinstance(value, dict) and value.get('type', '') == 'object':
            # Generate the default value from the embedded schema
            defaults[key] = _extract_default_values(value)

    return defaults


def _merge_options(first, second, overrides=True):
    """Merges the :code:`second` dictionary into the :code:`first` dictionary.
    If both dictionaries have the same key and both values are dictionaries
    then it recursively merges those two dictionaries.

    :param first: first dictionary
    :type first: dict
    :param second: second dictionary
    :type second: dict
    :param overrides: allow second to override first if both have same key
    :type overrides: bool
    :returns: merged dictionary
    :rtype: dict
    """

    result = copy.deepcopy(first)
    for key, second_value in second.items():
        if key in first:
            first_value = first[key]

            if (isinstance(first_value, collections.Mapping) and
               isinstance(second_value, collections.Mapping)):
                result[key] = _merge_options(first_value, second_value)
            elif not overrides and first_value != second_value:
                raise DCOSException(
                    "Trying to override package.json's key {} to {}".format(
                        key, second_value))
            else:
                result[key] = second_value
        else:
            result[key] = second_value

    return result


def resolve_package(package_name, config=None):
    """Returns the first package with the supplied name found by looking at
    the configured sources in the order they are defined.

    :param package_name: The name of the package to resolve
    :type package_name: str
    :param config: dcos config
    :type config: dcos.config.Toml | None
    :returns: The named package, if found
    :rtype: Package
    """

    if not config:
        config = util.get_config()

    for registry in registries(config):
        package = registry.get_package(package_name)
        if package:
            return package

    return None


def registries(config):
    """Returns configured cached package registries.

    :param config: Configuration dictionary
    :type config: dcos.config.Toml
    :returns: The list of registries, in resolution order
    :rtype: [Registry]
    """

    sources = list_sources(config)
    return [Registry(source, source.local_cache(config)) for source in sources]


def list_sources(config):
    """List configured package sources.

    :param config: Configuration dictionary
    :type config: dcos.config.Toml
    :returns: The list of sources, in resolution order
    :rtype: [Source]
    """

    source_uris = util.get_config_vals(['package.sources'], config)[0]

    sources = [url_to_source(s) for s in source_uris]

    errs = [source for source in sources if isinstance(source, Error)]
    if errs:
        raise DCOSException('\n'.join(err.error() for err in errs))

    return sources


def url_to_source(url):
    """Creates a package source from the supplied URL.

    :param url: Location of the package source
    :type url: str
    :returns: A Source backed by the supplied URL
    :rtype: Source | Error
    """

    parse_result = urllib.parse.urlparse(url)
    scheme = parse_result.scheme

    if scheme == 'file':
        return FileSource(url)
    elif scheme == 'http' or scheme == 'https':
        return HttpSource(url)
    elif scheme == 'git':
        return GitSource(url)
    else:
        return Error("Source URL uses unsupported protocol [{}]".format(url))


def _acquire_file_lock(lock_file_path):
    """Acquires an exclusive lock on the supplied file.

    :param lock_file_path: Path to the lock file
    :type lock_file_path: str
    :returns: Lock file
    :rtype: File
    """

    try:
        lock_file = open(lock_file_path, 'w')
    except IOError as e:
        logger.exception('Failed to open lock file: %s', lock_file_path)

        raise util.io_exception(lock_file_path, e.errno)

    acquire_mode = portalocker.LOCK_EX | portalocker.LOCK_NB

    try:
        portalocker.lock(lock_file, acquire_mode)
        return lock_file
    except portalocker.LockException:
        logger.exception(
            'Failure while tring to aquire file lock: %s',
            lock_file_path)

        lock_file.close()
        raise DCOSException('Unable to acquire the package cache lock')


class Source:
    """A source of DCOS packages."""

    @property
    @abc.abstractmethod
    def url(self):
        """
        :returns: Location of the package source
        :rtype: str
        """

        raise NotImplementedError

    def hash(self):
        """Returns a cryptographically secure hash derived from this source.

        :returns: a hexadecimal string
        :rtype: str
        """

        return hashlib.sha1(self.url.encode('utf-8')).hexdigest()

    def local_cache(self, config):
        """Returns the file system path to this source's local cache.

        :param config: Configuration dictionary
        :type config: dcos.config.Toml
        :returns: Path to this source's local cache on disk
        :rtype: str or None
        """

        cache_dir = os.path.expanduser(
            util.get_config_vals(['package.cache'], config)[0])
        return os.path.join(cache_dir, self.hash())

    def copy_to_cache(self, target_dir):
        """Copies the source content to the supplied local directory.

        :param target_dir: Path to the destination directory.
        :type target_dir: str
        :rtype: None
        """

        raise NotImplementedError

    def __repr__(self):

        return self.url


class FileSource(Source):
    """A registry of DCOS packages.

    :param url: Location of the package source
    :type url: str
    """

    def __init__(self, url):
        self._url = url

    @property
    def url(self):
        """
        :returns: Location of the package source
        :rtype: str
        """

        return self._url

    def copy_to_cache(self, target_dir):
        """Copies the source content to the supplied local directory.

        :param target_dir: Path to the destination directory.
        :type target_dir: str
        :rtype: None
        """

        # copy the source to the target_directory
        parse_result = urllib.parse.urlparse(self._url)
        source_dir = parse_result.path
        try:
            shutil.copytree(source_dir, target_dir)
            return None
        except OSError:
            logger.exception(
                'Error copying source director [%s] to target directory [%s].',
                source_dir,
                target_dir)

            raise DCOSException(
                'Unable to fetch packages from [{}]'.format(self.url))


class HttpSource(Source):
    """A registry of DCOS packages.

    :param url: Location of the package source
    :type url: str
    """

    def __init__(self, url):
        self._url = url

    @property
    def url(self):
        """
        :returns: Location of the package source
        :rtype: str
        """

        return self._url

    def copy_to_cache(self, target_dir):
        """Copies the source content to the supplied local directory.

        :param target_dir: Path to the destination directory.
        :type target_dir: str
        :returns: The error, if one occurred
        :rtype: None
        """

        try:
            with util.tempdir() as tmp_dir:

                tmp_file = os.path.join(tmp_dir, 'packages.zip')
                # Download the zip file.
                req = http.get(self.url)
                if req.status_code == 200:
                    with open(tmp_file, 'wb') as f:
                        for chunk in req.iter_content(1024):
                            f.write(chunk)
                else:
                    raise Exception(
                        'HTTP GET for {} did not return 200: {}'.format(
                            self.url,
                            req.status_code))

                # Unzip the downloaded file.
                packages_zip = zipfile.ZipFile(tmp_file, 'r')
                packages_zip.extractall(tmp_dir)

                # Move the enclosing directory to the target directory
                enclosing_dirs = [item
                                  for item in os.listdir(tmp_dir)
                                  if os.path.isdir(
                                      os.path.join(tmp_dir, item))]

                # There should only be one directory present after extracting.
                assert(len(enclosing_dirs) is 1)

                enclosing_dir = os.path.join(tmp_dir, enclosing_dirs[0])

                shutil.copytree(enclosing_dir, target_dir)

                # Set appropriate file permissions on the scripts.
                x_mode = (stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                          stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP)

                scripts_dir = os.path.join(target_dir, 'scripts')
                scripts = os.listdir(scripts_dir)

                for script in scripts:
                    script_path = os.path.join(scripts_dir, script)
                    if os.path.isfile(script_path):
                        os.chmod(script_path, x_mode)

                return None

        except Exception:
            logger.exception('Unable to fetch packages from URL: %s', self.url)

            raise DCOSException(
                'Unable to fetch packages from [{}]'.format(self.url))


class GitSource(Source):
    """A registry of DCOS packages.

    :param url: Location of the package source
    :type url: str
    """

    def __init__(self, url):
        self._url = url

    @property
    def url(self):
        """
        :returns: Location of the package source
        :rtype: str
        """

        return self._url

    def copy_to_cache(self, target_dir):
        """Copies the source content to the supplied local directory.

        :param target_dir: Path to the destination directory.
        :type target_dir: str
        :returns: The error, if one occurred
        :rtype: None
        """

        try:
            # TODO(SS): add better url parsing

            # Ensure git is installed properly.
            git_program = util.which('git')
            if git_program is None:
                raise DCOSException("""Could not locate the git program.  Make sure \
it is installed and on the system search path.
PATH = {}""".format(os.environ[constants.PATH_ENV]))

            # Clone git repo into the supplied target directory.
            git.Repo.clone_from(self._url,
                                to_path=target_dir,
                                progress=None,
                                branch='master')

            # Remove .git directory to save space.
            shutil.rmtree(os.path.join(target_dir, ".git"),
                          onerror=_rmtree_on_error)
            return None

        except git.exc.GitCommandError:
            logger.exception('Unable to fetch packages from git: %s', self.url)

            raise DCOSException(
                'Unable to fetch packages from [{}]'.format(self.url))


def _rmtree_on_error(func, path, exc_info):
    """Error handler for ``shutil.rmtree``.
    If the error is due to an access error (read only file)
    it attempts to add write permission and then retries.
    If the error is for another reason it re-raises the error.

    Usage : ``shutil.rmtree(path, onerror=onerror)``.

    :param func: Function which raised the exception.
    :type func: function
    :param path: The path name passed to ``shutil.rmtree`` function.
    :type path: str
    :param exc_info: Information about the last raised exception.
    :type exc_info: tuple
    :rtype: None
    """
    import stat
    if not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
        func(path)
    else:
        raise


class Error(errors.Error):
    """Class for describing errors during packaging operations.

    :param message: Error message
    :type message: str
    """

    def __init__(self, message):
        self._message = message

    def error(self):
        """Return error message

        :returns: The error message
        :rtype: str
        """

        return self._message


class Registry():
    """Represents a package registry on disk.

    :param base_path: Path to the registry
    :type base_path: str
    :param source: The associated package source
    :type source: Source
    """

    def __init__(self, source, base_path):
        self._base_path = base_path
        self._source = source

    def validate(self):
        """Validates a package registry.

        :returns: Validation errors
        :rtype: [str]
        """

        # TODO(CD): implement these checks in pure Python?
        scripts_dir = os.path.join(self._base_path, 'scripts')
        if util.is_windows_platform():
            validate_script = os.path.join(scripts_dir,
                                           '1-validate-packages.ps1')
            cmd = ['powershell', '-ExecutionPolicy',
                   'ByPass', '-File', validate_script]
            result = subprocess.call(cmd)
        else:
            validate_script = os.path.join(scripts_dir,
                                           '1-validate-packages.sh')
            result = subprocess.call(validate_script)
        if result is not 0:
            return ["Source tree is not valid [{}]".format(self._base_path)]
        else:
            return []

    @property
    def source(self):
        """Returns the associated upstream package source for this registry.

        :rtype: Source
        """

        return self._source

    def check_version(self, min_version, max_version):
        """Checks that the version is [min_version, max_version)

        :param min_version: the min version inclusive
        :type min_version: LooseVersion
        :param max_version: the max version exclusive
        :type max_version: LooseVersion
        :returns: None
        """

        version = LooseVersion(self.get_version())
        if not (version >= min_version and
                version < max_version):
            raise DCOSException((
                'Unable to update source [{}] because version {} is '
                'not supported. Supported versions are between {} and '
                '{}. Please update your DCOS CLI.').format(
                    self._source.url,
                    version,
                    min_version,
                    max_version))

    def get_version(self):
        """Returns the version of this registry.

        :rtype: str
        """

        # The package version is found in $BASE/repo/meta/version.json
        index_path = os.path.join(
            self._base_path,
            'repo',
            'meta',
            'version.json')

        if not os.path.isfile(index_path):
            raise DCOSException('Path [{}] is not a file'.format(index_path))

        try:
            with util.open_file(index_path) as fd:
                version_json = json.load(fd)
                return version_json.get('version')
        except ValueError:
            logger.exception('Unable to parse JSON: %s', index_path)

            raise DCOSException('Unable to parse [{}]'.format(index_path))

    def get_index(self):
        """Returns the index of packages in this registry.

        :rtype: dict
        """

        # The package index is found in $BASE/repo/meta/index.json
        index_path = os.path.join(
            self._base_path,
            'repo',
            'meta',
            'index.json')

        if not os.path.isfile(index_path):
            raise DCOSException('Path [{}] is not a file'.format(index_path))

        try:
            with util.open_file(index_path) as fd:
                return json.load(fd)
        except ValueError:
            logger.exception('Unable to parse JSON: %s', index_path)

            raise DCOSException('Unable to parse [{}]'.format(index_path))

    def get_package(self, package_name):
        """Returns the named package, if it exists.

        :param package_name: The name of the package to fetch
        :type package_name: str
        :returns: The requested package
        :rtype: Package
        """

        if len(package_name) is 0:
            raise DCOSException('Package name must not be empty.')

        # Packages are found in $BASE/repo/package/<first_character>/<pkg_name>
        first_character = package_name[0].title()

        package_path = os.path.join(
            self._base_path,
            'repo',
            'packages',
            first_character,
            package_name)

        if not os.path.isdir(package_path):
            return None

        try:
            return Package(self, package_path)
        except:
            logger.exception('Unable to read package: %s', package_path)

            raise DCOSException(
                'Could not read package [{}]'.format(package_name))


class Package():
    """Interface to a package on disk.

    :param registry: The containing registry for this package.
    :type registry: Registry
    :param path: Path to the package description on disk
    :type path: str
    """

    def __init__(self, registry, path):
        assert os.path.isdir(path)
        self._registry = registry
        self._path = path

    def name(self):
        """Returns the package name.

        :returns: The name of this package
        :rtype: str
        """

        return os.path.basename(self._path)

    def options(self, revision, user_options):
        """Merges package options with user supplied options, validates, and
        returns the result.

        :param revision: the package revision to install
        :type revision: str
        :param user_options: package parameters
        :type user_options: dict
        :returns: a dictionary with the user supplied options
        :rtype: dict
        """

        if user_options is None:
            user_options = {}

        config_schema = self.config_json()
        default_options = _extract_default_values(config_schema)
        if default_options is None:
            pkg = self.package_json(revision)
            msg = ("An object in the package's config.json is missing the "
                   "required 'properties' feature:\n {}".format(config_schema))
            if 'maintainer' in pkg:
                msg += "\nPlease contact the project maintainer: {}".format(
                       pkg['maintainer'])
            raise DCOSException(msg)

        logger.info('Generated default options: %r', default_options)

        # Merge option overrides, second argument takes precedence
        options = _merge_options(default_options, user_options)

        logger.info('Merged options: %r', options)

        # Validate options with the config schema
        errs = util.validate_json(options, config_schema)
        if len(errs) != 0:
            raise DCOSException(
                "{}\n\n{}".format(
                    util.list_to_err(errs),
                    'Please create a JSON file with the appropriate options, '
                    'and pass the /path/to/file as an --options argument.'))

        return options

    def registry(self):
        """Returns the containing registry for this package.

        :rtype: Registry
        """

        return self._registry

    def get_path(self):
        """Returns the path on disk to this package.

        :rtype: str
        """

        return self._path

    def has_definition(self, revision, filename):
        """Returns true if the package defines filename; false otherwise.

        :param revision: package revision
        :type revision: str
        :param filename: file in package definition
        :type filename: str
        :returns: whether filename is defined
        :rtype: bool
        """

        return os.path.isfile(
            os.path.join(
                self._path,
                os.path.join(revision, filename)))

    def has_command_definition(self, revision):
        """Returns true if the package defines a command; false otherwise.

        :param revision: package revision
        :type revision: str
        :rtype: bool
        """

        return self.has_definition(revision, 'command.json')

    def _has_resource_definition(self, revision):
        """Returns true if the package defines a resource; false otherwise.

        :param revision: package revision
        :type revision: str
        :rtype: bool
        """

        return self.has_definition(revision, 'resource.json')

    def has_marathon_definition(self, revision):
        """Returns true if the package defines a Marathon json. false otherwise.

        :param revision: package revision
        :type revision: str
        :rtype: bool
        """

        return self.has_definition(revision, 'marathon.json')

    def has_marathon_mustache_definition(self, revision):
        """Returns true if the package defines a Marathon.json.mustache false
        otherwise.

        :param revision: package revision
        :type revision: str
        :rtype: bool
        """

        return self.has_definition(revision, 'marathon.json.mustache')

    def _get_marathon_json_file(self, revision):
        """Returns the file name of Marathon json

        :param revision: package revision
        :type revision: str
        :returns: Marathon file name
        :rtype: str
        """
        if self.has_marathon_definition(revision):
            return 'marathon.json'
        elif self.has_marathon_mustache_definition(revision):
            return 'marathon.json.mustache'
        else:
            raise DCOSException("Missing Marathon json definition of package")

    def config_json(self, revision):
        """Returns the JSON content of the config.json file.

        :param revision: package revision
        :type revision: str
        :returns: Package config schema
        :rtype: dict
        """

        return self._json(revision, 'config.json')

    def package_json(self, revision):
        """Returns the JSON content of the package.json file.

        :param revision: the package revision
        :type revision: str
        :returns: Package data
        :rtype: dict
        """

        return self._json(revision, 'package.json')

    def _resource_json(self, revision):
        """Returns the JSON content of the resource.json file.

        :param revision: the package revision
        :type revision: str
        :returns: Package data
        :rtype: dict
        """

        return self._json(revision, 'resource.json')

    def marathon_json(self, revision, options):
        """Returns the JSON content of the marathon.json template, after
        rendering it with options.

        :param revision: the package revision
        :type revision: str
        :param options: the template options to use in rendering
        :type options: dict
        :rtype: dict
        """

        marathon_file = self._get_marathon_json_file(revision)
        if self.has_marathon_mustache_definition(revision) and \
                self._has_resource_definition():
            resources = {"resource": self._resource_json()}
            options = _merge_options(options, resources, False)
        init_desc = self._render_template(
            marathon_file,
            revision,
            options)

        # Add package metadata
        package_labels = self._make_package_labels(options)

        # Preserve existing labels
        labels = init_desc.get('labels', {})

        labels.update(package_labels)
        init_desc['labels'] = labels

        return init_desc

    def command_json(self, revision, options):
        """Returns the JSON content of the command.json template, after
        rendering it with options.

        :param revision: the package revision
        :type revision: str
        :param options: the template options to use in rendering
        :type options: dict
        :returns: Package data
        :rtype: dict
        """

        template = self._data(revision, 'command.json')
        rendered = pystache.render(template, options)
        return json.loads(rendered)

    def marathon_template(self, revision):
        """ Returns raw data from marathon.json

        :param revision: the package revision
        :type revision: str
        :returns: raw data from marathon.json
        :rtype: str
        """
        return self._data(revision, self._get_marathon_json_file(revision))

    def command_template(self, revision):
        """ Returns raw data from command.json

        :param revision: the package revision
        :type revision: str
        :returns: raw data from command.json
        :rtype: str
        """
        return self._data(revision, 'command.json')

    def _render_template(self, name, revision, options):
        """Render a template.

        :param name: the file name of the template
        :type name: str
        :param revision: the package revision
        :type revision: str
        :param options: the template options to use in rendering
        :type options: dict
        :rtype: dict
        """

        template = self._data(revision, name)
        return util.render_mustache_json(template, options)

    def _json(self, revision, name):
        """Returns the json content of the file named `name` in the directory
           named `revision`

        :param revision: the package revision
        :type revision: str
        :param name: file name
        :type name: str
        :rtype: dict
        """

        data = self._data(revision, name)
        logger.info("JSON {}".format(data))
        return util.load_jsons(data)

    def _data(self, revision, name):
        """Returns the content of the file named `name` in the directory named
        `revision`

        :param revision: the package revision
        :type revision: str
        :param name: file name
        :type name: str
        :returns: File content of the supplied path
        :rtype: str
        """

        path = os.path.join(revision, name)
        full_path = os.path.join(self._path, path)
        return util.read_file(full_path)

    def package_revisions(self):
        """Returns all of the available package revisions, most recent first.

        :returns: Available revisions of this package
        :rtype: [str]
        """

        vs = sorted((f for f in os.listdir(self._path)
                     if not f.startswith('.')), key=int, reverse=True)
        return vs

    def package_revisions_map(self):
        """Returns an ordered mapping from the package revision to the package
           version, sorted by package revision.

        :returns: Map from package revision to package version
        :rtype: OrderedDict
        """

        package_version_map = collections.OrderedDict()
        for rev in self.package_revisions():
            pkg_json = Package.package_json(self, rev)
            package_version_map[rev] = pkg_json['version']
        return package_version_map

    def package_versions(self):
        """Returns a list of available versions for this package

        :returns: package version
        :rtype: []
        """
        revision_map = self.package_revisions_map()
        return list(revision_map.values())

    def latest_package_revision(self, package_version=None):
        """Returns the most recent package revision, for a
        given package version if specified.

        :param package_version: a given package version
        :type package_version: str
        :returns: package revision
        :rtype: str | None
        """

        if package_version:
            pkg_rev_map = self.package_revisions_map()
            # depends on package_revisions() returning an OrderedDict
            if package_version in pkg_rev_map.values():
                return next(pkg_rev for pkg_rev in reversed(pkg_rev_map)
                            if pkg_rev_map[pkg_rev] == package_version)
            else:
                return None
        else:
            pkg_revisions = self.package_revisions()
            revision = pkg_revisions[0]

        return revision

    def __repr__(self):

        rev = self.latest_package_revision()
        pkg_json = self.package_json(rev)

        return json.dumps(pkg_json)


class PackageVersion(Package):
    """Interface to a specific package version on disk"""

    def __init__(self, name, version, revision, registry, path):
        self._name = name
        self._revision = revision
        self._package_version = version
        self._registry = registry
        self._path = path

    def name(self):
        """Returns the package name.

        :returns: The name of this package
        :rtype: str
        """

        return self._name

    def version(self):
        """Returns the package version.

        :returns: The version of this package
        :rtype: str
        """

        return self._package_version

    def revision(self):
        """Returns the package version.

        :returns: The version of this package
        :rtype: str
        """

        return self._revision

    def package_json(self):
        """Returns the JSON content of the package.json file.

        :returns: Package data
        :rtype: dict
        """

        return Package.package_json(self, self._revision)

    def marathon_json(self, options):
        """Returns the JSON content of the marathon.json template, after
        rendering it with options.

        :param options: the template options to use in rendering
        :type options: dict
        :rtype: dict
        """

        return Package.marathon_json(self, self._revision, options)

    def has_command_definition(self):
        """Returns true if the package defines a command; false otherwise.

        :rtype: bool
        """

        return Package.has_command_definition(self, self._revision)

    def command_json(self, options):
        """Returns the JSON content of the comand.json template, after
        rendering it with options.

        :param options: the template options to use in rendering
        :type options: dict
        :returns: Package subcommand data
        :rtype: dict
        """

        return Package.command_json(self, self._revision, options)

    def config_json(self):
        """Returns the JSON content of the config.json file.

        :returns: Package config schema
        :rtype: dict
        """

        return Package.config_json(self, self._revision)

    def options(self, user_options):
        """Merges package options with user supplied options, validates, and
        returns the result.

        :param user_options: package parameters
        :type user_options: dict
        :returns: a dictionary with the user supplied options
        :rtype: dict
        """

        return Package.options(self, self._revision, user_options)

    def has_mustache_definition(self):
        """Returns true if the package defines a Marathon json or mustache.
        false otherwise.

        :rtype: bool
        """

        return self.has_marathon_definition(self._revision) or \
            self.has_marathon_mustache_definition(self._revision)

    def _has_resource_definition(self):
        """Returns true if the package defines a resource; false otherwise.

        :rtype: bool
        """

        return Package._has_resource_definition(self, self._revision)

    def _resource_json(self):
        """Returns the JSON content of the resource.json file.

        :returns: Package resources
        :rtype: dict
        """

        return Package._resource_json(self, self._revision)

    def marathon_template(self):
        """Returns raw data from marathon.json

        :returns: raw data from marathon.json
        :rtype: str
        """

        return Package.marathon_template(self, self._revision)

    def command_template(self):
        """ Returns raw data from command.json

        :returns: raw data from command.json
        :rtype: str
        """
        return Package.command_template(self, self._revision)

    def _make_package_labels(self, options):
        """Returns Marathon app labels for a package.

        :param pkg: The package to install
        :type pkg: Package
        :param revision: The package revision to install
        :type revision: str
        :param options: package parameters
        :type options: dict
        :returns: Marathon app labels
        :rtype: dict
        """

        metadata = self.package_json()
        # add images to package.json metadata for backwards compatability
        # in the UI
        if self._has_resource_definition():
            images = {"images": self._resource_json()["images"]}
            metadata.update(images)

        encoded_metadata = _base64_encode(metadata)

        is_framework = metadata.get('framework')
        if not is_framework:
            is_framework = False

        package_registry_version = self.registry().get_version()

        package_labels = {
            PACKAGE_METADATA_KEY: encoded_metadata,
            PACKAGE_NAME_KEY: self.name(),
            PACKAGE_VERSION_KEY: self.version(),
            PACKAGE_SOURCE_KEY: self.registry().source.url,
            PACKAGE_FRAMEWORK_KEY: json.dumps(is_framework),
            PACKAGE_REGISTRY_VERSION_KEY: package_registry_version,
            PACKAGE_RELEASE_KEY: self._revision
        }

        if self.has_command_definition():
            command = self.command_json(options)
            package_labels[PACKAGE_COMMAND_KEY] = _base64_encode(command)

        # Run a heuristic that determines the hint for the framework name
        framework_name = _find_framework_name(self.name(), options)
        if framework_name:
            package_labels[PACKAGE_FRAMEWORK_NAME_KEY] = framework_name

        return package_labels


class IndexEntries():
    """A collection of package index entries from a single source.
    Each entry is a dict as described by the JSON schema for the package index:
    https://github.com/mesosphere/universe/blob/master/repo/meta/schema/index-schema.json

    :param source: The source of these index entries
    :type source: Source
    :param packages: The index entries
    :type packages: [dict]
    """

    def __init__(self, source, packages):
        self._source = source
        self._packages = packages

    @property
    def source(self):
        """Returns the source of these index entries.

        :rtype: Source
        """

        return self._source

    @property
    def packages(self):
        """Returns the package index entries.

        :rtype: list of dict
        """

        return self._packages

    def as_dict(self):
        """
        :rtype: dict
        """

        return {'packages': self.packages}


def get_apps_for_framework(framework_name, client):
    """ Return all apps running the given framework.

    :param framework_name: framework name
    :type framework_name: str
    :param client: marathon client
    :type client: marathon.Client
    :rtype: [dict]
    """

    return [app for app in client.get_apps()
            if app.get('labels', {}).get(
                PACKAGE_FRAMEWORK_NAME_KEY) == framework_name]


class PackageManager():
    """Package Manager using local file system"""

    def install_app(self, pkg, options, app_id):
        """Installs a package's application

        :param pkg: the package to install
        :type pkg: PackageVersion
        :param revision: the package revision to install
        :type revision: str
        :param options: user supplied options
        :type options: dict
        :param app_id: app ID for installation of this package
        :type app_id: str
        :rtype: None
        """

        config = util.get_config()
        init_client = marathon.create_client(config)

        # Insert option parameters into the init template
        init_desc = pkg.marathon_json(options)

        if app_id is not None:
            logger.debug('Setting app ID to "%s" (was "%s")',
                         app_id,
                         init_desc['id'])
            init_desc['id'] = app_id

        # Send the descriptor to init
        init_client.add_app(init_desc)

    def uninstall_app(self, app_name, remove_all, app_id):
        """Uninstalls an app.

        :param app_name: The app to uninstall
        :type app_name: str
        :param remove_all: Whether to remove all instances of the named app
        :type remove_all: boolean
        :param app_id: App ID of the app instance to uninstall
        :type app_id: str
        :returns: whether uninstall was successful or not
        :rtype: bool
        """

        init_client = marathon.create_client()
        dcos_client = mesos.DCOSClient()
        apps = init_client.get_apps()

        def is_match(app):
            # We normalize encoding for byte-wise comparison
            encoding = 'utf-8'
            name_label = app.get('labels', {}).get(PACKAGE_NAME_KEY, u'')
            name_label_enc = name_label.encode(encoding)
            app_name_enc = app_name.encode(encoding)
            name_matches = name_label_enc == app_name_enc

            if app_id is not None:
                pkg_app_id = app.get('id', '')
                normalized_app_id = init_client.normalize_app_id(app_id)
                return name_matches and pkg_app_id == normalized_app_id
            else:
                return name_matches

        matching_apps = [a for a in apps if is_match(a)]

        if not remove_all and len(matching_apps) > 1:
            app_ids = [a.get('id') for a in matching_apps]
            raise DCOSException(
                ("Multiple apps named [{}] are installed: [{}].\n" +
                 "Please use --app-id to specify the ID of the app to" +
                 " uninstall, or use --all to uninstall all apps.").format(
                    app_name,
                    ', '.join(app_ids)))

        for app in matching_apps:
            package_json = _decode_and_add_context(
                app['id'],
                app.get('labels', {}))

            # First, remove the app from Marathon
            init_client.remove_app(app['id'], force=True)

            # Second, shutdown the framework with Mesos
            framework_name = app.get('labels', {}).get(
                PACKAGE_FRAMEWORK_NAME_KEY)
            if framework_name is not None:
                logger.info(
                    'Trying to shutdown framework {}'.format(framework_name))
                frameworks = mesos.Master(dcos_client.get_master_state()) \
                    .frameworks(inactive=True)

                # Look up all the framework names
                framework_ids = [
                    framework['id']
                    for framework in frameworks
                    if framework['name'] == framework_name
                ]

                logger.info(
                    'Found the following frameworks: {}'.format(framework_ids))

                # Emit post uninstall notes
                emitter.publish(
                    DefaultError(
                        'Uninstalled package [{}] version [{}]'.format(
                            package_json['name'],
                            package_json['version'])))

                if 'postUninstallNotes' in package_json:
                    emitter.publish(
                        DefaultError(package_json['postUninstallNotes']))

                if len(framework_ids) == 1:
                    dcos_client.shutdown_framework(framework_ids[0])
                elif len(framework_ids) > 1:
                    raise DCOSException(
                        "Unable to shutdown the framework for [{}] because "
                        "there are multiple frameworks with the same name: "
                        "[{}]. Manually shut them down using 'dcos service "
                        "shutdown'.".format(
                            framework_name,
                            ', '.join(framework_ids)))

        return len(matching_apps) > 0

    def search_sources(self, query):
        """Returns a dict of index entry collections, one for each registry
        in the supllied config

        :param query: The search term
        :type query: str
        :rtype: [IndexEntries]
        """
        config = util.get_config()
        results = [index_entry.as_dict() for index_entry in
                   search(query, config)]

        return results

    def get_package_version(self, package_name, package_version):
        """Returns PackageVersion of specified package

        :param package_name: package name
        :type package_name: str
        :param package_version: version of package
        :type package_version: str | None
        :rtype: PackageVersion

        """
        pkg = resolve_package(package_name)
        if pkg is None:
            msg = "Package [{}] not found".format(package_name)
            raise DCOSException(msg)

        pkg_revision = pkg.latest_package_revision(package_version)
        if pkg_revision is None:
            if package_version is not None:
                msg = "Version {} of package [{}] is not available".format(
                    package_version, package_name)
            else:
                msg = "Package [{}] not available".format(package_name)
            raise DCOSException(msg)

        if package_version is None:
            revision_map = pkg.package_revisions_map()
            package_version = revision_map.get(pkg_revision)

        return PackageVersion(package_name, package_version, pkg_revision,
                              pkg.registry(), pkg.get_path())

    def installed_apps(package_name, app_id, endpoints=False):
        """Returns all installed apps.  An app is of the format:

        {
            'appId': <appId>,
            'packageSource': <source>,
            'releaseVersion': <release_version>
            'endpoints' (optional): [{
                'host': <host>,
                'ports': <ports>,
            }]
            ..<package.json properties>..
        }

        :param endpoints: Whether to include a list of endpoints as port-host
                          pairs
        :type endpoints: boolean
        :returns: all installed apps
        :rtype: [dict]
        """

        init_client = marathon.create_client()
        apps = init_client.get_apps()

        encoded_apps = [(a['id'], a['labels'])
                        for a in apps
                        if a.get('labels', {}).get(PACKAGE_METADATA_KEY)]

        # Filter elements that failed to parse correctly as JSON
        valid_apps = []
        for app_id, labels in encoded_apps:
            try:
                decoded = _decode_and_add_context(app_id, labels)
            except Exception:
                logger.exception(
                    'Unable to decode package metadata during install: %s',
                    app_id)

            valid_apps.append(decoded)

        if endpoints:
            for app in valid_apps:
                tasks = init_client.get_tasks(app["appId"])
                app['endpoints'] = [{"host": t["host"], "ports": t["ports"]}
                                    for t in tasks]

        return valid_apps

    def update_sources(self, validate=False):
        """Overwrites the local package cache with the latest source data.

        :param validate: Whether or not to validate package sources
        :type validate: bool
        :rtype: None
        """

        config = util.get_config()
        errors = []

        # ensure the cache directory is properly configured
        cache_dir = os.path.expanduser(
            util.get_config_vals(['package.cache'], config)[0])

        # ensure the cache directory exists
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)

        if not os.path.isdir(cache_dir):
            raise DCOSException(
                'Cache directory does not exist! [{}]'.format(cache_dir))

        # obtain an exclusive file lock on $CACHE/.lock
        lock_path = os.path.join(cache_dir, '.lock')

        with _acquire_file_lock(lock_path):

            # list sources
            sources = list_sources(config)

            for source in sources:

                emitter.publish('Updating source [{}]'.format(source))

                # create a temporary staging directory
                with util.tempdir() as tmp_dir:

                    stage_dir = os.path.join(tmp_dir, source.hash())

                    # copy to the staging directory
                    try:
                        source.copy_to_cache(stage_dir)
                    except DCOSException as e:
                        logger.exception(
                            'Failed to copy universe source %s to cache %s',
                            source.url,
                            stage_dir)

                        errors.append(str(e))
                        continue

                    # check version
                    # TODO(jsancio): move this to the validation when forced
                    Registry(source, stage_dir).check_version(
                        LooseVersion('1.0'),
                        LooseVersion('3.0'))

                    # validate content
                    if validate:
                        validation_errors = Registry(source,
                                                     stage_dir).validate()
                        if len(validation_errors) > 0:
                            errors += validation_errors
                            continue  # keep updating the other sources

                    # remove the $CACHE/source.hash() directory
                    target_dir = os.path.join(cache_dir, source.hash())
                    try:
                        if os.path.exists(target_dir):
                            shutil.rmtree(target_dir,
                                          onerror=_rmtree_on_error,
                                          ignore_errors=False)
                    except OSError:
                        logger.exception(
                            'Error removing target directory before move: %s',
                            target_dir)

                        err = "Could not remove directory [{}]".format(
                            target_dir)
                        errors.append(err)
                        continue  # keep updating the other sources

                    # move the staging directory to $CACHE/source.hash()
                    shutil.move(stage_dir, target_dir)

        if errors:
            raise DCOSException(util.list_to_err(errors))
