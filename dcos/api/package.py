import hashlib
import logging
import os
import shutil
import subprocess

import git
import portalocker
from dcos.api import errors, util

try:
    # Python 2
    from urlparse import urlparse
except ImportError:
    # Python 3
    from urllib.parse import urlparse


def list_sources(config):
    """List configured package sources.

    :param config: Configuration dictionary
    :type config: config.Toml
    :returns: The list of sources, in resolution order
    :rtype: (list of Source, list of Error)
    """

    source_uris = config.get('package.sources')

    if source_uris is None:
        config_error = Error('No configured value for [package.sources]')
        return (None, [config_error])

    results = [url_to_source(s) for s in config['package.sources']]
    sources = [source for (source, _) in results if source is not None]
    errors = [error for (_, error) in results if error is not None]
    return (sources, errors)


def url_to_source(url):
    """Creates a package source from the supplied URL.

    :param url: Location of the package source
    :type url: str
    :returns: A Source backed by the supplied URL
    :rtype: (Source, Error)
    """

    parse_result = urlparse(url)
    scheme = parse_result.scheme

    if scheme == 'file':
        return (FileSource(url), None)

    elif scheme == 'http' or scheme == 'https':
        return (HttpSource(url), None)

    elif scheme == 'git':
        return (GitSource(url), None)

    else:
        err = Error("Source URL uses unsupported protocol [{}]".format(url))
        return (None, err)


def acquire_file_lock(lock_file_path):
    """Acquires an exclusive lock on the supplied file.

    "param lock_file_path: Path to the lock file
    :type lock_file_path: str
    :returns: Lock file descriptor
    :rtype: (file_descriptor, Error)
    """

    lock_fd = open(lock_file_path, 'w')
    acquire_mode = portalocker.LOCK_EX | portalocker.LOCK_NB

    try:
        portalocker.lock(lock_fd, acquire_mode)
        return (lock_fd, None)
    except portalocker.LockException:
        lock_fd.close()
        return (None, Error("Unable to acquire the package cache lock"))


def update_sources(config):
    """Overwrites the local package cache with the latest source data.

    :param config: Configuration dictionary
    :type config: config.Toml
    :returns: Error, if any.
    :rtype: list of Error
    """

    errors = []

    # ensure the cache directory is properly configured
    cache_dir = config.get('package.cache')

    if cache_dir is None:
        config_error = Error("No configured value for [package.cache]")
        errors.append(config_error)
        return errors

    # ensure the cache directory exists
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    if not os.path.isdir(cache_dir):
        err = Error('Cache directory does not exist! [{}]'.format(cache_dir))
        errors.append(err)
        return errors

    # obtain an exclusive file lock on $CACHE/.lock
    lock_path = os.path.join(cache_dir, '.lock')
    lock_fd, lock_error = acquire_file_lock(lock_path)

    if lock_error is not None:
        errors.append(lock_error)
        return errors

    with lock_fd:

        # list sources
        sources, list_errors = list_sources(config)

        if len(list_errors) > 0:
            errors = errors + list_errors
            return errors

        for source in sources:

            logging.info("Updating source [%s]", source)

            # create a temporary staging directory
            with util.tempdir() as tmp_dir:

                stage_dir = os.path.join(tmp_dir, source.hash())

                # copy to the staging directory
                copy_err = source.copy_to_cache(stage_dir)
                if copy_err is not None:
                    errors.append(copy_err)
                    continue  # keep updating the other sources

                # validate content
                validation_errors = Registry(stage_dir).validate()
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

                # rename the staging directory as $CACHE/source.hash()
                os.rename(stage_dir, target_dir)

    return errors


class Source:
    """A source of DCOS packages."""

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

    def copy_to_cache(self, target_dir):
        """Copies the source content to the supplied local directory.

        :returns: The error, if one occurred
        :rtype: Error
        """

        raise NotImplementedError


class FileSource(Source):
    """A registry of DCOS packages."""

    def __init__(self, url):
        """
        :param url: Location of the package source
        :type url: str
        """

        self.url = url

    def url(self):
        return self.url

    def copy_to_cache(self, target_dir):
        # copy the source to the target_directory
        parse_result = urlparse(self.url)
        source_dir = parse_result.path
        try:
            shutil.copytree(source_dir, target_dir)
            return None
        except OSError:
            return Error('Could not copy [{}] to [{}]'.format(source_dir,
                                                              target_dir))


class HttpSource(Source):
    """A registry of DCOS packages."""

    def __init__(self, url):
        """
        :param url: Location of the package source
        :type url: str
        """

        self.url = url

    def url(self):
        return self.url

    def copy_to_cache(self, target_dir):
        raise NotImplementedError


class GitSource(Source):
    """A registry of DCOS packages."""

    def __init__(self, url):
        """
        :param url: Location of the package source
        :type url: str
        """

        self.url = url

    def url(self):
        return self.url

    def copy_to_cache(self, target_dir):
        try:
            # TODO: add better url parsing
            # clone git repo into the supplied target_dir
            git.Repo.clone_from(self.url,
                                to_path=target_dir,
                                progress=None,
                                branch='master')
            # remove .git directory to save space
            shutil.rmtree(os.path.join(target_dir, ".git"))
            return None
        except git.exc.GitCommandError:
            return Error("Unable to clone [{}] to [{}]".format(self.url,
                                                               target_dir))


class Error(errors.Error):
    def __init__(self, message):
        """Constructs error for packages and sources

        :param message: Error message
        :type message: str
        """

        self._message = message

    def error(self):
        """Return error message

        :returns: The error message
        :rtype: str
        """

        return self._message


class Registry():
    """Represents a package registry on disk."""

    def __init__(self, base_path):
        self.base_path = base_path

    def validate(self):
        """Validates a package registry.

        :returns: Validation errors
        :rtype: list of Error
        """

        # TODO(CD): implement these checks in pure Python?
        scripts_dir = os.path.join(self.base_path, 'scripts')
        validate_script = os.path.join(scripts_dir, '1-validate-packages.sh')
        errors = []
        result = subprocess.call(validate_script)
        if result is not 0:
            err = Error('Source tree is not valid [{}]'.format(self.base_path))
            errors.append(err)

        return errors
