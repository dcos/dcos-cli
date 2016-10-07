import collections

import docopt

import dcoscli
from dcos import cmds, config, emitting, http, util
from dcos.errors import DCOSException, DefaultError
from dcoscli.subcommand import default_command_info, default_doc
from dcoscli.util import decorate_docopt_usage

emitter = emitting.FlatEmitter()
logger = util.get_logger(__name__)


def main(argv):
    try:
        return _main(argv)
    except DCOSException as e:
        emitter.publish(e)
        return 1


@decorate_docopt_usage
def _main(argv):
    args = docopt.docopt(
        default_doc("config"),
        argv=argv,
        version='dcos-config version {}'.format(dcoscli.version))

    http.silence_requests_warnings()

    return cmds.execute(_cmds(), args)


def _cmds():
    """
    :returns: all the supported commands
    :rtype: list of dcos.cmds.Command
    """

    return [
        cmds.Command(
            hierarchy=['config', 'set'],
            arg_keys=['<name>', '<value>'],
            function=_set),

        cmds.Command(
            hierarchy=['config', 'unset'],
            arg_keys=['<name>'],
            function=_unset),

        cmds.Command(
            hierarchy=['config', 'show'],
            arg_keys=['<name>'],
            function=_show),

        cmds.Command(
            hierarchy=['config', 'validate'],
            arg_keys=[],
            function=_validate),

        cmds.Command(
            hierarchy=['config'],
            arg_keys=['--info'],
            function=_info),
    ]


def _info(info):
    """
    :param info: Whether to output a description of this subcommand
    :type info: boolean
    :returns: process status
    :rtype: int
    """

    emitter.publish(default_command_info("config"))
    return 0


def _set(name, value):
    """
    :returns: process status
    :rtype: int
    """

    if name == "package.sources":
        notice = ("This config property has been deprecated. "
                  "Please add your repositories with `dcos package repo add`")
        return DCOSException(notice)
    if name == "core.email":
        notice = "This config property has been deprecated."
        return DCOSException(notice)

    toml, msg = config.set_val(name, value)
    emitter.publish(DefaultError(msg))

    return 0


def _unset(name):
    """
    :returns: process status
    :rtype: int
    """

    msg = config.unset(name)
    emitter.publish(DefaultError(msg))

    return 0


def _show(name):
    """
    :returns: process status
    :rtype: int
    """

    toml_config = config.get_config(True)

    if name is not None:
        value = toml_config.get(name)
        if value is None:
            raise DCOSException("Property {!r} doesn't exist".format(name))
        elif isinstance(value, collections.Mapping):
            raise DCOSException(config.generate_choice_msg(name, value))
        else:
            emitter.publish(value)
    else:
        # Let's list all of the values
        for key, value in sorted(toml_config.property_items()):
            if key == "core.dcos_acs_token":
                value = "*"*8
            emitter.publish('{} {}'.format(key, value))

    return 0


def _validate():
    """
    :returns: process status
    :rtype: int
    """

    toml_config = config.get_config(True)

    errs = util.validate_json(toml_config._dictionary,
                              config.generate_root_schema(toml_config))
    if len(errs) != 0:
        emitter.publish(util.list_to_err(errs))
        return 1

    emitter.publish("Congratulations, your configuration is valid!")
    return 0
