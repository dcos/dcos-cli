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

    toml, msg = config.set_val(name, value)
    emitter.publish(DefaultError(msg))

    if name == "core.dcos_url" and config.uses_deprecated_config():
        notice = (
            "Setting-up a cluster through this command is being deprecated. "
            "To setup the CLI to talk to your cluster, please run "
            "`dcos cluster setup <dcos_url>`.")
        emitter.publish(DefaultError(notice))

    return 0


def _unset(name):
    """
    :returns: process status
    :rtype: int
    """

    msg = config.unset(name)
    emitter.publish(DefaultError(msg))

    return 0


def _format_config(file_value, effective_value, name=None, envvar_name=None):
    """
    Construct a string to show on a terminal, indicating the value and
    possibly other useful things such as the setting name and whether
    it is being controlled by an environment variable.

    >>> _format_config('x', 'x')
    'x'
    >>> _format_config('x', 'x', 'setting.name') ->
    'setting.name x'
    >>> _format_config('x', 'y', envvar_name='ENVVAR')
    'y # overwritten by ENVVAR; config file value: x'
    >>> _format_config('x', 'y', 'setting.name', envvar_name='ENVVAR')
    'setting.name y   # overwritten by ENVVAR; config file value: x'

    :param file_value: config value present in the toml file
    :type file_value: str

    :param effective_value: config value either from file or as overwritten
                            from the environment
    :type effective_value: str
    :param name: config key (not used for single value show)
    :type name: str|None
    :param envvar_name: name of environment variable that overwote the value
    :type envvar_name: str|None
    :returns: formatted string for terminal
    :rtype: str
    """

    # when declaring that vars are overwritten by the environment,
    # line up those messages to this column (unless the var name is long)
    overwite_msg_display_column = 35

    # When showing all values, don't print the token value;
    if name == "core.dcos_acs_token":
        print_value = "*"*8
    else:
        print_value = effective_value

    if file_value == effective_value:
        if name:
            return '%s %s' % (name, print_value)
        else:
            return effective_value
    else:
        if not envvar_name:
            envvar_name = "N/A"  # this should never happen
        if name:
            s = '%s %s' % (name, print_value)
        else:
            s = effective_value

        left_pad_fmt = '%-{}s'.format(overwite_msg_display_column)  # '%-35s'

        msg_start = left_pad_fmt + ' # overwritten by environment var %s; '

        if print_value != effective_value:
            # We're obscuring the effective security token
            # so don't report the file value either
            msg = msg_start + "config file value differs"
            return msg % (s, envvar_name)

        msg = msg_start + 'config file value: %s'
        return msg % (s, envvar_name, file_value)


def _show(name):
    """
    :returns: process status
    :rtype: int
    """

    toml_config = config.get_config(True)

    if name is not None:
        file_value = toml_config.get(name)
        try:
            # If the user presented a partial key name, eg 'core' when
            # we have 'core.xyz'; we will get an exception here
            effective_value, envvar_name = config.get_config_val_envvar(name)
        except DCOSException as e:
            # The expected case of a partial key name has special
            # handling via this mechanism.
            if isinstance(file_value, collections.Mapping):
                exc_msg = config.generate_choice_msg(name, file_value)
                raise DCOSException(exc_msg)
            raise  # Unexpected errors, pass right along

        if effective_value is None:
            raise DCOSException("Property {!r} doesn't exist".format(name))
        else:
            msg = _format_config(file_value, effective_value,
                                 envvar_name=envvar_name)
            emitter.publish(msg)

    else:
        # Let's list all of the values
        for key, value in sorted(toml_config.property_items()):
            file_value = toml_config.get(key)
            effective_value, envvar_name = config.get_config_val_envvar(key)

            msg = _format_config(file_value, effective_value, key,
                                 envvar_name=envvar_name)
            emitter.publish(msg)

    return 0


def _validate():
    """
    :returns: process status
    :rtype: int
    """

    toml_config = config.get_config(True)

    emitter.publish('Validating %s ...' % config.get_config_path())
    errs = util.validate_json(toml_config._dictionary,
                              config.generate_root_schema(toml_config))
    if len(errs) != 0:
        emitter.publish(util.list_to_err(errs))
        return 1

    emitter.publish("Congratulations, your configuration is valid!")
    return 0
