package cmd

import (
	"bytes"
	"fmt"
	"io"
	"strings"

	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/dcos/dcos-cli/pkg/plugin"
	"github.com/spf13/cobra"
)

const (
	dcosReloadReplacementTarget = `__start_dcos()
{`
	// This has a workaround to allow this auto-reload method to work on older versions of bash.
	// Specifically 3.2 which is the default bash installed on macOS.
	dcosReloadReplacementResult = `__start_dcos()
{
    source /dev/stdin <<<"$(dcos completion %s)"`
)

func newCompletionCommand(ctx *cli.Context, plugins []*plugin.Plugin) *cobra.Command {
	cmd := &cobra.Command{
		Use:       "completion",
		ValidArgs: []string{"bash", "zsh"},
		RunE: func(cmd *cobra.Command, args []string) error {
			shell := args[0]

			// add the subcommands and their associated data to the root plugin commands
			for _, p := range plugins {
				p.AddCompletionData()
			}

			buffer := &bytes.Buffer{}

			switch shell {
			case "bash":
				cmd.Root().GenBashCompletion(buffer)
			case "zsh":
				zshCompletion(cmd.Root(), buffer)
			default:
			}

			replaceWithShell := fmt.Sprintf(dcosReloadReplacementResult, shell)
			outStr := strings.Replace(buffer.String(), dcosReloadReplacementTarget, replaceWithShell, 1)

			fmt.Fprint(ctx.Out(), outStr)

			return nil
		},
	}

	return cmd
}

func zshCompletion(root *cobra.Command, out io.Writer) {
	// All of this is lifted directly from kubectl's zsh completion which relies on cobra's
	// bash completion. Cobra has built in zsh completion generation but it seems to be fairly
	// limited at this time.
	zshHead := "#compdef dcos\n"

	out.Write([]byte(zshHead))

	zshInitialization := `
__dcos_bash_source() {
    alias shopt=':'
    alias _expand=_bash_expand
    alias _complete=_bash_comp
    emulate -L sh
    setopt kshglob noshglob braceexpand
    source "$@"
}
__dcos_type() {
    # -t is not supported by zsh
    if [ "$1" == "-t" ]; then
        shift
        # fake Bash 4 to disable "complete -o nospace". Instead
        # "compopt +-o nospace" is used in the code to toggle trailing
        # spaces. We don't support that, but leave trailing spaces on
        # all the time
        if [ "$1" = "__dcos_compopt" ]; then
            echo builtin
            return 0
        fi
    fi
    type "$@"
}
__dcos_compgen() {
    local completions w
    completions=( $(compgen "$@") ) || return $?
    # filter by given word as prefix
    while [[ "$1" = -* && "$1" != -- ]]; do
        shift
        shift
    done
    if [[ "$1" == -- ]]; then
        shift
    fi
    for w in "${completions[@]}"; do
        if [[ "${w}" = "$1"* ]]; then
            echo "${w}"
        fi
    done
}
__dcos_compopt() {
    true # don't do anything. Not supported by bashcompinit in zsh
}
__dcos_ltrim_colon_completions()
{
    if [[ "$1" == *:* && "$COMP_WORDBREAKS" == *:* ]]; then
        # Remove colon-word prefix from COMPREPLY items
        local colon_word=${1%${1##*:}}
        local i=${#COMPREPLY[*]}
        while [[ $((--i)) -ge 0 ]]; do
            COMPREPLY[$i]=${COMPREPLY[$i]#"$colon_word"}
        done
    fi
}
__dcos_get_comp_words_by_ref() {
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[${COMP_CWORD}-1]}"
    words=("${COMP_WORDS[@]}")
    cword=("${COMP_CWORD[@]}")
}
__dcos_filedir() {
    local RET OLD_IFS w qw
    __dcos_debug "_filedir $@ cur=$cur"
    if [[ "$1" = \~* ]]; then
        # somehow does not work. Maybe, zsh does not call this at all
        eval echo "$1"
        return 0
    fi
    OLD_IFS="$IFS"
    IFS=$'\n'
    if [ "$1" = "-d" ]; then
        shift
        RET=( $(compgen -d) )
    else
        RET=( $(compgen -f) )
    fi
    IFS="$OLD_IFS"
    IFS="," __dcos_debug "RET=${RET[@]} len=${#RET[@]}"
    for w in ${RET[@]}; do
        if [[ ! "${w}" = "${cur}"* ]]; then
            continue
        fi
        if eval "[[ \"\${w}\" = *.$1 || -d \"\${w}\" ]]"; then
            qw="$(__dcos_quote "${w}")"
            if [ -d "${w}" ]; then
                COMPREPLY+=("${qw}/")
            else
                COMPREPLY+=("${qw}")
            fi
        fi
    done
}
__dcos_quote() {
    if [[ $1 == \'* || $1 == \"* ]]; then
        # Leave out first character
        printf %q "${1:1}"
    else
        printf %q "$1"
    fi
}
autoload -U +X bashcompinit && bashcompinit
# use word boundary patterns for BSD or GNU sed
LWORD='[[:<:]]'
RWORD='[[:>:]]'
if sed --help 2>&1 | grep -q GNU; then
    LWORD='\<'
    RWORD='\>'
fi
__dcos_convert_bash_to_zsh() {
    sed \
    -e 's/declare -F/whence -w/' \
    -e 's/_get_comp_words_by_ref "\$@"/_get_comp_words_by_ref "\$*"/' \
    -e 's/local \([a-zA-Z0-9_]*\)=/local \1; \1=/' \
    -e 's/flags+=("\(--.*\)=")/flags+=("\1"); two_word_flags+=("\1")/' \
    -e 's/must_have_one_flag+=("\(--.*\)=")/must_have_one_flag+=("\1")/' \
    -e "s/${LWORD}_filedir${RWORD}/__dcos_filedir/g" \
    -e "s/${LWORD}_get_comp_words_by_ref${RWORD}/__dcos_get_comp_words_by_ref/g" \
    -e "s/${LWORD}__ltrim_colon_completions${RWORD}/__dcos_ltrim_colon_completions/g" \
    -e "s/${LWORD}compgen${RWORD}/__dcos_compgen/g" \
    -e "s/${LWORD}compopt${RWORD}/__dcos_compopt/g" \
    -e "s/${LWORD}declare${RWORD}/builtin declare/g" \
    -e "s/\\\$(type${RWORD}/\$(__dcos_type/g" \
    <<'BASH_COMPLETION_EOF'
`
	out.Write([]byte(zshInitialization))

	buf := new(bytes.Buffer)
	root.GenBashCompletion(buf)
	out.Write(buf.Bytes())

	zshTail := `
BASH_COMPLETION_EOF
}
__dcos_bash_source <(__dcos_convert_bash_to_zsh)
_complete dcos 2>/dev/null
`
	out.Write([]byte(zshTail))
}
