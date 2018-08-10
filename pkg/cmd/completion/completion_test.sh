#!/usr/local/bin/bash

. completion.sh
. /usr/local/etc/bash_completion

# this will reset the completion variables between each run
setUp() {
    COMP_LINE=""
    COMP_POINT=0
    COMP_WORDS=()
    COMP_CWORD=0

    COMPREPLY=()
}

setTest() { COMP_LINE="$1"
    COMP_POINT="${#COMP_LINE}"
    eval set -- "$COMP_LINE"
    COMP_WORDS=(${COMP_LINE[@]})
    # add space if there is a space at the end of the input string
    [[ ${COMP_LINE[@]: -1} = ' ' ]] && COMP_WORDS+=('')
    COMP_CWORD=$(( ${#COMP_WORDS[@]} - 1 ))

}

checkCompreplyVals() {
    local i=0 w expected equal=0
    expected=("$@")
    assertEquals "completions array is incorrect length" "${#expected[@]}" "${#COMPREPLY[@]}"

    while [ "$i" -lt "${#expected}" ]; do
        w="${expected[$i]}"
        if [[ "$w" != "${COMPREPLY[$i]}" ]]; then
            equal=1
            break
        fi
        ((i++))
    done

    assertTrue "not all values in output equal. expected: <${expected[*]}> was <${COMPREPLY[*]}>" $equal
}

testRootCommands() {
    expected=("auth " "cluster " "config " "help " "plugin ")
    setTest "dcos "
    __dcos_main

    checkCompreplyVals "${expected[@]}"

}

testPartialComplete() {
    expected=("cluster ")
    setTest "dcos cl"
    __dcos_main

    checkCompreplyVals "${expected[@]}"
}

testAuthCommands() {
    expected=("list-providers " "login " "logout ")
    setTest "dcos auth "
    __dcos_main

    checkCompreplyVals "${expected[@]}"
}

. shunit2
