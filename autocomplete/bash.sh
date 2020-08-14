_transcriptic_completion() {
    COMPREPLY=( $( env COMP_WORDS="${COMP_WORDS[*]}" \
                   COMP_CWORD=$COMP_CWORD \
                   _TRANSCRIPTIC_COMPLETE=complete $1 ) )
    return 0
}

complete -F _transcriptic_completion -o default transcriptic;
