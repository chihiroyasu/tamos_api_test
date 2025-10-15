#!/bin/bash
#REF: https://stackoverflow.com/questions/29010999/how-to-assign-echo-value-to-a-variable-in-shell
{
    ifs=$'\n' read -r -d '' stderr;
    ifs=$'\n' read -r -d '' stdout;
} < <((printf '\0%s\0' "$(/home/user/.pyenv/shims/python /home/user/toms-server/tamc/services/backend/manualObs/getSunImage/getSunImage.py)" 1>&2) 2>&1)

if [ -n "$stdout" ]
then
    echo -e "$stdout\n" >> /home/user/toms-server/tamc/services/backend/manualObs/getSunImage/log/regularlySun.log
fi

if [ -n "$stderr" ]
then
    date +"[%y-%m-%d %H:%M:%S]" | awk -v var="$stderr" '{print $0,var}' >> /home/user/toms-server/tamc/services/backend/manualObs/getSunImage/log/regularlySun-error.log
fi