#!/bin/bash

# __dcos_<helper func>
# _dcos_<cli subcommand>

__dcos_debug() {
    if [[ -n ${DCOS_COMP_DEBUG_FILE} ]]; then
        echo "${FUNCNAME[1]}: $*" >> "${DCOS_COMP_DEBUG_FILE}"
    fi
} 


# Default behavior to get the next command from the current command. In the case of --help and maybe other situations
# in the future that should end completion, this returns 1, otherwise 0
#
# Assumes a $command variable exists in the calling context that will contain the found subcommand
# Assumes a $c variable exists in the calling context that is the current
# word being evaluated from the input string (this is defined in __dcos_main so shouldn't be a problem)
__dcos_default_command_parse() {
    while [ "$c" -lt "$cword" ]; do
        i="${words[c]}"
        case "$i" in
            --help)
                # if help is present as a flag, cobra will ignore everything after so stop completion
                return 1
                ;;
            -*) ;;
            *)
                command="$i";
                # $c is effectively global so that way it can crawl through the arguments as the program
                # navigates the function tree and so $c will always be the next unread word
                # after finding the next command, we increment $c before breaking out of the loop
                ((c++))
                break
                ;;
        esac
        ((c++))
    done
    return 0
}

__dcos_handle_compreply() {
    __dcos_debug "completions: $*"

    local i=0

    for completion in "$@"; do
        # filter out completions which don't match the current word
        if [[ $completion == "$cur"* ]]; then
            # check if the completion offered is a flag that accepts an argument which is marked by an =
            # if so, a space is not manually added since the user is expected to add further input
            case "$completion" in
                --*=*)
                    COMPREPLY[i++]="$completion"
                    ;;
                *)
                    COMPREPLY[i++]="$completion "
                    ;;
            esac
        fi
    done
}

# Calls next subcommand by our calling conventions.
# TODO: argument handling can probably be done more explicitly
# This assumes the following variables exist in the calling scope and are correct:
# commands: array of subcommands this function holds
# command: the command to call into
__dcos_handle_subcommand() {

    # if a command was given, check that it is an actual command and call the associated function
    for cmd in "${commands[@]}"; do
        if [[ $cmd == "$command" ]]; then
            __dcos_debug "found subcommand: $cmd"

            local subcommand next_command
            # swap - in commands names for _
            subcommand=${command//-/_}

            __dcos_debug "calling into function ${last_command}_${subcommand}"
            next_command=${last_command}_${subcommand}
            last_command=$next_command

            $next_command
            return
        fi
    done
}

_dcos_auth() {
	local i command

    if ! __dcos_default_command_parse; then
        return
    fi

    local commands=("list-providers" "login" "logout")
    local flags=("--help")

    if [ -z "$command" ]; then
        case "$cur" in
            --*)
                __dcos_handle_compreply "${flags[@]}"
                ;;
            *)
                __dcos_handle_compreply "${commands[@]}"
                ;;
        esac
        return
    fi

    __dcos_handle_subcommand
}

_dcos_auth_login() {
	local i command

    if ! __dcos_default_command_parse; then
        return
    fi

    local flags=( "--help"
    "--password="
    "--password-file="
    "--private-key="
    "--provider="
    "--username="
    )

    if [ -z "$command" ]; then
        case "$cur" in
            --*=*)
                # don't support flag argument completion yet
                return
                ;;
            --*)
                __dcos_handle_compreply "${flags[@]}"
                ;;
            *) ;;
        esac
        return
    fi

}

_dcos_auth_list_providers() {
	local i command

    if ! __dcos_default_command_parse; then
        return
    fi

    local flags=("--help" "--json")

    if [ -z "$command" ]; then
        case "$cur" in
            --*=*)
                # don't support flag argument completion yet
                return
                ;;
            --*)
                __dcos_handle_compreply "${flags[@]}"
                ;;
            *) ;;
        esac
        return
    fi
}

_dcos_auth_logout() {
	local i command

    if ! __dcos_default_command_parse; then
        return
    fi

    local flags=("--help")

    if [ -z "$command" ]; then
        case "$cur" in
            --*=*)
                # don't support flag argument completion yet
                return
                ;;
            --*)
                __dcos_handle_compreply "${flags[@]}"
                ;;
            *) ;;
        esac
        return
    fi
}

_dcos_cluster() {
    local i command

    if ! __dcos_default_command_parse; then
        return 
    fi

    local commands=("attach" "help" "list" "remove" "rename" "setup")
    local flags=("--help")

    if [ -z "$command" ]; then
        case "$cur" in
            --*)
                __dcos_handle_compreply "${flags[@]}"
                ;;
            *)
                __dcos_handle_compreply "${commands[@]}"
                ;;
        esac
        return
    fi

    __dcos_handle_subcommand
}

_dcos_cluster_attach() {
    local i command

    if ! __dcos_default_command_parse; then
        return
    fi

    local flags=("--help")

    if [ -z "$command" ]; then
        case "$cur" in
            --*=*)
                # don't support flag argument completion yet
                return
                ;;
            --*)
                __dcos_handle_compreply "${flags[@]}"
                ;;
            *) ;;
        esac
        return
    fi
}

_dcos_cluster_help() {
    :
}

_dcos_cluster_list() {
    :
}

_dcos_cluster_remove() {
    :
}

_dcos_cluster_rename() {
    :
}

_dcos_cluster_setup() {
    :
}

_dcos_config() {
    :
}

_dcos_help() {
    :
}

_dcos_plugin() {
    :
}


_dcos() {
	local i c=1 command

    if ! __dcos_default_command_parse; then
        return
    fi

    local commands=("auth" "cluster" "config" "help" "plugin")
    local flags=("--help" "--version")

    local plugin_commands=$(dcos plugin list --commands)
    commands+=(${plugin_commands[@]})
    __dcos_debug "Found plugin commands ${plugin_commands[@]}"

    local completion_dirs=$(dcos plugin list --completion-dirs)
    __dcos_debug "Plugin completion directories ${completion_dirs[@]}"


    # no subcommand given, complete either flags or subcommands
    if [ -z "$command" ]; then
        case "$cur" in
        --*=*)
            # TODO: don't support flag completion right now
            # this does leave out the potential for detecting flags that take values but are separated like
            # --flag value instead of --flag=value
            # we're not worrying about flag arg completion yet though so it's safe to ignore that
            return
            ;;
        --*)
            __dcos_handle_compreply "${flags[@]}"
            ;;
        *)
            # no command was given so list out possible subcommands
            __dcos_handle_compreply "${commands[@]}"
            ;;
        esac
        return
    fi

    __dcos_handle_subcommand
}

__dcos_main() {
    __dcos_debug "$@"

    local cur prev words cword last_command
    # give last_command the root prefix
    last_command="_dcos"

    COMPREPLY=()

    # this function exists in the bash-completion package which I believe must
    # be installed separately from bash
    _get_comp_words_by_ref -n "=:" cur prev words cword

    __dcos_debug "Starting completion on $cur from ${words[*]}"

    _dcos
}

complete -o bashdefault -o default -o nospace -F __dcos_main dcos
