import abc
import base64
import collections
import copy
import hashlib
import json
import os
import shutil
import stat
import subprocess
import zipfile

import git
import portalocker
import pystache
import six
from dcos import constants, emitting, errors, marathon, subcommand, util
from dcos.errors import DCOSException

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


def install_app(pkg, version, init_client, options, app_id):
    """Installs a package's application

    :param pkg: the package to install
    :type pkg: Package
    :param version: the package version to install
    :type version: str
    :param init_client: the program to use to run the package
    :type init_client: object
    :param options: package parameters
    :type options: dict
    :param app_id: app ID for installation of this package
    :type app_id: str
    :rtype: None
    """

    # Insert option parameters into the init template
    init_desc = pkg.marathon_json(version, options)

    if app_id is not None:
        logger.debug('Setting app ID to "%s" (was "%s")',
                     app_id,
                     init_desc['id'])
        init_desc['id'] = app_id

    # Send the descriptor to init
    init_client.add_app(init_desc)


def _make_package_labels(pkg, version, options):
    """Returns Marathon app labels for a package.

    :param pkg: The package to install
    :type pkg: Package
    :param version: The package version to install
    :type version: str
    :param options: package parameters
    :type options: dict
    :returns: Marathon app labels
    :rtype: dict
    """

    metadata = pkg.package_json(version)

    encoded_metadata = _base64_encode(metadata)

    is_framework = metadata.get('framework')
    if not is_framework:
        is_framework = False

    package_registry_version = pkg.registry.get_version()

    package_labels = {
        PACKAGE_METADATA_KEY: encoded_metadata,
        PACKAGE_NAME_KEY: metadata['name'],
        PACKAGE_VERSION_KEY: metadata['version'],
        PACKAGE_SOURCE_KEY: pkg.registry.source.url,
        PACKAGE_FRAMEWORK_KEY: json.dumps(is_framework),
        PACKAGE_REGISTRY_VERSION_KEY: package_registry_version,
        PACKAGE_RELEASE_KEY: str(version)
    }

    if pkg.is_command_defined(version):
        command = pkg.command_json(version, options)
        package_labels[PACKAGE_COMMAND_KEY] = _base64_encode(command)

    # Run a heuristic that determines the hint for the framework name
    framework_name = _find_framework_name(pkg.name(), options)
    if framework_name:
        package_labels[PACKAGE_FRAMEWORK_NAME_KEY] = framework_name

    return package_labels


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


def uninstall(package_name, remove_all, app_id, cli, app):
    """Uninstalls a package.

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
        init_client = marathon.create_client()

        num_apps = uninstall_app(package_name,
                                 remove_all,
                                 app_id,
                                 init_client)

        if num_apps > 0:
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


def uninstall_app(app_name, remove_all, app_id, init_client):
    """Uninstalls an app.

    :param app_name: The app to uninstall
    :type app_name: str
    :param remove_all: Whether to remove all instances of the named app
    :type remove_all: boolean
    :param app_id: App ID of the app instance to uninstall
    :type app_id: str
    :param init_client: The program to use to run the app
    :type init_client: object
    :returns: number of apps uninstalled
    :rtype: int
    """

    apps = init_client.get_apps()

    def is_match(app):
        encoding = 'utf-8'  # We normalize encoding for byte-wise comparison
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
        raise DCOSException("""Multiple instances of app [{}] are installed. \
Please specify the app id of the instance to uninstall or uninstall all. \
The app ids of the installed package instances are: [{}].""".format(
            app_name, ', '.join(app_ids)))

    for app in matching_apps:
        init_client.remove_app(app['id'], force=True)

    return len(matching_apps)


class InstalledPackage(object):
    """Represents an intalled DCOS package.  One of `app` and
    `subcommand` must be supplied.

    :param app: A dictionary representing a marathon app.  Of the
                format returned by `installed_apps()`
    :type app: dict
    :param subcommand: Installed subcommand
    :type subcommand: subcommand.InstalledSubcommand
    """

    def __init__(self, app=None, subcommand=None):
        assert app or subcommand
        self.app = app
        self.subcommand = subcommand

    def name(self):
        """
        :returns: The name of the package
        :rtype: str
        """
        if self.subcommand:
            return self.subcommand.name
        else:
            return self.app['name']

    def dict(self):
        """ A dictionary representation of the package.  Used by `dcos package
        list-installed`.

        :returns: A dictionary representation of the package.
        :rtype: dict
        """
        ret = {'name': self.name}

        if self.subcommand:
            ret['command'] = {'name': self.subcommand.name}

        if self.app:
            ret['app'] = {'appId': self.app['appId']}

        if self.subcommand:
            package_json = self.subcommand.package_json()
            ret.update(package_json)

            ret['packageSource'] = self.subcommand.package_source()
            ret['releaseVersion'] = self.subcommand.package_version()
        else:
            ret.update(self.app)
            ret.pop('appId')

        return ret


def installed_packages(init_client, endpoints):
    """Returns all installed packages in the format:

    [{
       'app': {
         'id': <id>
       },
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

    apps = installed_apps(init_client, endpoints)
    subcommands = installed_subcommands()

    dicts = collections.defaultdict(lambda: {'app': None, 'command': None})

    for app in apps:
        key = (app['name'], app['releaseVersion'], app['packageSource'])
        dicts[key]['app'] = app

    for subcmd in subcommands:
        package_version = subcmd.package_version()
        package_source = subcmd.package_source()
        key = (subcmd.name, package_version, package_source)
        dicts[key]['command'] = subcmd

    pkgs = []

    for key, pkg in dicts.items():
        pkgs.append(InstalledPackage(pkg['app'], pkg['command']))

    return pkgs


def installed_subcommands():
    """Returns all installed subcommands.

    :returns: all installed subcommands
    :rtype: [InstalledSubcommand]
    """

    return [subcommand.InstalledSubcommand(name) for name in
            subcommand.distributions(util.dcos_path())]


def installed_apps(init_client, endpoints=False):
    """
    Returns all installed apps.  An app is of the format:

    {
      'appId': <appId>,
      'packageSource': <source>,
      'registryVersion': <app_version>,
      'releaseVersion': <release_version>
      'endpoints' (optional): [{
        'host': <host>,
        'ports': <ports>,
      }]
      ..<package.json properties>..
    }

    :param init_client: The program to use to list packages
    :type init_client: object
    :param endpoints: Whether to include a list of
                      endpoints as port-host pairs
    :type endpoints: boolean
    :returns: all installed apps
    :rtype: [dict]
    """

    apps = init_client.get_apps()

    encoded_apps = [(a['id'], a['labels'])
                    for a in apps
                    if a.get('labels', {}).get(PACKAGE_METADATA_KEY)]

    def decode_and_add_context(pair):
        app_id, labels = pair
        encoded = labels.get(PACKAGE_METADATA_KEY, {})
        decoded = base64.b64decode(six.b(encoded)).decode()

        decoded_json = util.load_jsons(decoded)
        decoded_json['appId'] = app_id
        decoded_json['packageSource'] = labels.get(PACKAGE_SOURCE_KEY)
        decoded_json['releaseVersion'] = labels.get(PACKAGE_RELEASE_KEY)
        return decoded_json

    # Filter elements that failed to parse correctly as JSON
    valid_apps = []
    for encoded in encoded_apps:
        try:
            decoded = decode_and_add_context(encoded)
        except Exception as e:
            logger.exception(e)

        valid_apps.append(decoded)

    if endpoints:
        for app in valid_apps:
            tasks = init_client.get_tasks(app["appId"])
            app['endpoints'] = [{"host": t["host"], "ports": t["ports"]}
                                for t in tasks]

    return valid_apps


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

    q = query.lower()

    result = 0.0
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
    :rtype: dict
    """

    defaults = {}
    for key, value in config_schema['properties'].items():
        if 'default' in value:
            defaults[key] = value['default']
        elif value.get('type', '') == 'object':
            # Generate the default value from the embedded schema
            defaults[key] = _extract_default_values(value)

    return defaults


def _merge_options(first, second):
    """Merges the :code:`second` dictionary into the :code:`first` dictionary.
    If both dictionaries have the same key and both values are dictionaries
    then it recursively merges those two dictionaries.

    :param first: first dictionary
    :type first: dict
    :param second: second dictionary
    :type second: dict
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
            else:
                result[key] = second_value
        else:
            result[key] = second_value

    return result


def resolve_package(package_name, config):
    """Returns the first package with the supplied name found by looking at
    the configured sources in the order they are defined.

    :param package_name: The name of the package to resolve
    :type package_name: str
    :param config: Configuration dictionary
    :type config: dcos.config.Toml
    :returns: The named package, if found
    :rtype: Package
    """

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

    source_uris = config.get('package.sources')

    if source_uris is None:
        raise DCOSException('No configured value for [package.sources]')

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
    :returns: Lock file descriptor
    :rtype: File
    """

    lock_fd = open(lock_file_path, 'w')
    acquire_mode = portalocker.LOCK_EX | portalocker.LOCK_NB

    try:
        portalocker.lock(lock_fd, acquire_mode)
        return lock_fd
    except portalocker.LockException:
        lock_fd.close()
        raise DCOSException('Unable to acquire the package cache lock')


def update_sources(config, validate=False):
    """Overwrites the local package cache with the latest source data.

    :param config: Configuration dictionary
    :type config: dcos.config.Toml
    :rtype: None
    """

    errors = []

    # ensure the cache directory is properly configured
    cache_dir = config.get('package.cache')

    if cache_dir is None:
        raise DCOSException('No configured value for [package.cache]')

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
                    errors.append(e.message)
                    continue

                # validate content
                if validate:
                    validation_errors = Registry(source, stage_dir).validate()
                    if len(validation_errors) > 0:
                        errors += validation_errors
                        continue  # keep updating the other sources

                # remove the $CACHE/source.hash() directory
                target_dir = os.path.join(cache_dir, source.hash())
                try:
                    if os.path.exists(target_dir):
                        shutil.rmtree(target_dir, ignore_errors=False)
                except OSError:
                    err = Error(
                        'Could not remove directory [{}]'.format(target_dir))
                    errors.append(err)
                    continue  # keep updating the other sources

                # move the staging directory to $CACHE/source.hash()
                shutil.move(stage_dir, target_dir)

    if errors:
        raise DCOSException(util.list_to_err(errors))


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

        cache_dir = config.get('package.cache')
        if cache_dir is None:
            return None

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
                urllib.request.urlretrieve(self.url, tmp_file)

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
            shutil.rmtree(os.path.join(target_dir, ".git"))
            return None

        except git.exc.GitCommandError:
            raise DCOSException(
                'Unable to fetch packages from [{}]'.format(self.url))


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
        :rtype: [Error]
        """

        # TODO(CD): implement these checks in pure Python?
        scripts_dir = os.path.join(self._base_path, 'scripts')
        validate_script = os.path.join(scripts_dir, '1-validate-packages.sh')
        result = subprocess.call(validate_script)
        if result is not 0:
            return [Error(
                'Source tree is not valid [{}]'.format(self._base_path))]
        else:
            return []

    @property
    def source(self):
        """Returns the associated upstream package source for this registry.

        :rtype: Source
        """

        return self._source

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
            with open(index_path) as fd:
                version_json = json.load(fd)
                return version_json.get('version')
        except IOError:
            raise DCOSException('Unable to open file [{}]'.format(index_path))
        except ValueError:
            raise DCOSException('Unable to parse [{}]'.format(index_path))

    def get_index(self):
        """Retuprns the index of packages in this registry.

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
            with open(index_path) as fd:
                return json.load(fd)
        except IOError:
            raise DCOSException('Unable to open file [{}]'.format(index_path))
        except ValueError:
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
        self.path = path

    def name(self):
        """Returns the package name.

        :returns: The name of this package
        :rtype: str
        """

        return os.path.basename(self.path)

    def options(self, version, user_options):
        """Merges package options with user supplied options, validates, and
        returns the result.

        :param version: the package version to install
        :type version: str
        :param user_options: package parameters
        :type user_options: dict
        :returns: a dictionary with the user supplied options
        :rtype: dict
        """

        if user_options is None:
            user_options = {}

        config_schema = self.config_json(version)
        default_options = _extract_default_values(config_schema)

        logger.info('Generated default options: %r', default_options)

        # Merge option overrides
        options = _merge_options(default_options, user_options)

        logger.info('Merged options: %r', options)

        # Validate options with the config schema
        errs = util.validate_json(options, config_schema)
        if len(errs) != 0:
            raise DCOSException(util.list_to_err(errs))

        return options

    @property
    def registry(self):
        """Returns the containing registry for this package.

        :rtype: Registry
        """

        return self._registry

    def is_command_defined(self, version):
        """Returns true if the package defines a command; false otherwise.

        :param version: package version
        :type version: str
        :rtype: bool
        """

        return os.path.isfile(
            os.path.join(
                self.path,
                os.path.join(version, 'command.json')))

    def config_json(self, version):
        """Returns the JSON content of the config.json file.

        :returns: Package config schema
        :rtype: dict
        """

        return self._json(os.path.join(version, 'config.json'))

    def package_json(self, version):
        """Returns the JSON content of the package.json file.

        :param version: the package version
        :type version: str
        :returns: Package data
        :rtype: dict
        """

        return self._json(os.path.join(version, 'package.json'))

    def marathon_json(self, version, options):
        """Returns the JSON content of the marathon.json template, after
        rendering it with options.

        :param version: the package version
        :type version: str
        :param options: the template options to use in rendering
        :type options: dict
        :rtype: dict
        """

        init_desc = self._render_template(
            'marathon.json',
            version,
            options)

        # Add package metadata
        package_labels = _make_package_labels(self, version, options)

        # Preserve existing labels
        labels = init_desc.get('labels', {})

        labels.update(package_labels)
        init_desc['labels'] = labels

        return init_desc

    def command_json(self, version, options):
        """Returns the JSON content of the comand.json template, after
        rendering it with options.

        :param version: the package version
        :type version: str
        :param options: the template options to use in rendering
        :type options: dict
        :returns: Package data
        :rtype: dict
        """

        template = self._data(os.path.join(version, 'command.json'))
        rendered = pystache.render(template, options)
        return json.loads(rendered)

    def _render_template(self, name, version, options):
        """Render a template.

        :param name: the file name of the template
        :type name: str
        :param version: the package version
        :type version: str
        :param options: the template options to use in rendering
        :type options: dict
        :rtype: dict
        """

        template = self._data(os.path.join(version, name))
        return util.render_mustache_json(template, options)

    def _json(self, path):
        """Returns the json content of the supplied file, relative to the
        base path.

        :param path: The relative path to the file to read
        :type path: str
        :rtype: dict
        """

        data = self._data(path)
        return util.load_jsons(data)

    def _data(self, path):
        """Returns the content of the supplied file, relative to the base path.

        :param path: The relative path to the file to read
        :type path: str
        :returns: File content of the supplied path
        :rtype: str
        """

        full_path = os.path.join(self.path, path)
        return util.read_file(full_path)

    def package_versions(self):
        """Returns all of the available package versions, most recent first.

        Note that the result does not describe versions of the package, not
        the software described by the package.

        :returns: Available versions of this package
        :rtype: [str]
        """

        vs = [f for f in os.listdir(self.path) if not f.startswith('.')]
        vs.reverse()
        return vs

    def software_versions(self):
        """Returns a mapping from the package version to the version of the
        software described by the package.

        :returns: Map from package versions to versions of the softwre.
        :rtype: dict
        """

        software_package_map = collections.OrderedDict()
        for v in self.package_versions():
            pkg_json = self.package_json(v)
            software_package_map[v] = pkg_json['version']
        return software_package_map

    def latest_version(self):
        """Returns the latest package version.

        :returns: The latest version of this package
        :rtype: str
        """

        pkg_versions = self.package_versions()

        if len(pkg_versions) is 0:
            raise DCOSException(
                'No versions found for package [{}]'.format(self.name()))

        pkg_versions.sort()
        return pkg_versions[-1]

    def __repr__(self):

        v, error = self.latest_version()
        if error is not None:
            return error.error()

        pkg_json, error = self.package_json(v)

        if error is not None:
            return error.error()

        return json.dumps(pkg_json)


class IndexEntries():
    """A collection of package index entries from a single source.
    Each entry is a dict as described by the JSON schema for the package index:
    https://github.com/mesosphere/universe/blob/master/repo/meta/schema/index-schema.json

    :param source: The source of these index entries
    :type source: Source
    :param packages: The index entries
    :type packages: list of dict
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

        return {'source': self.source.url, 'packages': self.packages}
