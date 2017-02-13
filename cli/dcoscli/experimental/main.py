import base64
import json
import os
import shutil
import tempfile
import zipfile

import docopt
import pkg_resources
import six

import dcoscli
from dcos import cmds, emitting, http, options, servicemanager, util
from dcos.errors import DCOSException
from dcos.package import get_package_manager
from dcos.util import md5_hash_file
from dcoscli.subcommand import default_command_info, default_doc
from dcoscli.util import decorate_docopt_usage

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
        default_doc("experimental"),
        argv=argv,
        version='dcos-experimental version {}'.format(dcoscli.version))
    http.silence_requests_warnings()
    return cmds.execute(_cmds(), args)


def _cmds():
    """
    :returns: All of the supported commands
    :rtype: dcos.cmds.Command
    """
    return [
        cmds.Command(
            hierarchy=['experimental', 'package', 'add'],
            arg_keys=['--json', '--dcos-package',
                      '--package-name', '--package-version'],
            function=_add),
        cmds.Command(
            hierarchy=['experimental', 'package', 'build'],
            arg_keys=['--json', '<build-definition>', '--output-directory'],
            function=_build,
        ),
        cmds.Command(
            hierarchy=['experimental', 'service', 'start'],
            arg_keys=['--json', '<package-name>',
                      '--package-version', '--options'],
            function=_service_start),
        cmds.Command(
            hierarchy=['experimental'],
            arg_keys=['--info'],
            function=_experimental),
    ]


def _experimental(info):
    """
    :returns: process status
    :rtype: int
    """
    if info:
        emitter.publish(default_command_info("experimental"))
    else:
        doc = default_doc("package")
        emitter.publish(options.make_generic_usage_message(doc))
        return 1
    return 0


def _add(json, dcos_package, package_name, package_version):
    """
    Add a DC/OS package to DC/OS

    :param json: wether to output json
    :type json: bool
    :param dcos_package: path to the DC/OS package
    :type dcos_package: None | str
    :param package_name: the name of a remote DC/OS package
    :type package_name: None | str
    :param package_version: the version of a remote DC/OS package
    :type package_version: None | str
    :return: process status
    :rtype: int
    """
    package_manager = get_package_manager()
    if dcos_package:
        response = package_manager.package_add_local(dcos_package)
    else:
        response = (package_manager
                    .package_add_remote(package_name, package_version))

    response_json = response.json()

    if json:
        emitter.publish(response_json)
    else:
        message = (
            'The package [{}] version [{}] has been added to DC/OS'.format(
                response_json['name'], response_json['version']))
        emitter.publish(message)

    return 0


def _build(output_json,
           build_definition,
           output_directory):
    """ Creates a DC/OS Package from a DC/OS Package Build Definition

    :param output_json: whether to output json
    :type output_json: None | bool
    :param build_definition: The Path to a DC/OS package build definition
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
    manifest_json = {
        'built-by': "dcoscli.version={}".format(dcoscli.version)
    }

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

    if output_json:
        message = {'package_path': dcos_package_path}
    else:
        message = 'Created DC/OS Universe Package [{}]'.format(
            dcos_package_path)
    emitter.publish(message)

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
    :type item: str
    :returns: true if item is a local reference else false
    :rtype: bool
    """
    return isinstance(item, six.string_types) and item.startswith("@")


def _service_start(json, package_name, package_version, options_path):
    """Starts a DC/OS service from a package that has been added

    :param json: wether to output json
    :type json: bool
    :param package_name:
    :type package_name: str
    :param package_version:
    :type package_version: None | str
    :param options_path:
    :type options_path: None | str
    :return: process status
    :rtype: int
    """
    manager = servicemanager.ServiceManager()
    options = util.read_file_json(options_path) if options_path else None
    response = manager.start_service(
        package_name, package_version, options)
    response_json = response.json()

    if json:
        emitter.publish(response_json)
    else:
        message = (
            "The service [{}] version [{}] has been started".format(
                response_json['packageName'], response_json['packageVersion']
            ))
        emitter.publish(message)

    return 0
