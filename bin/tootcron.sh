#!/bin/bash

# this script is designed to run as a cronjob
# prerequisites:
# 0. install dependencies: poetry update
# 1. configure server: python -m tootroll --configure
#
# Example - run every 5 minutes:
# */5 * * * * cd ${REPO_DIRECTORY} && timeout 290 bash bin/tootcron.sh

PROFILE="private"

# cron defaults
CRON_SECONDS=300        # run every 5 minutes
CRON_OFFSET_SECONDS=0   # adjust possible offset

exit_on_fail() { echo $1; exit 1;}

# TOOTROLL_HOME is where data gets stored
# if not defined in environment, defaults to $HOME/.tootroll
if [[ -z "$TOOTROLL_HOME" ]];then
    export TOOTROLL_HOME="$HOME"/.tootroll
fi

# run via Poetry (virtualenv) if installed
POETRY_EXEC="/usr/local/bin/poetry"
if [[ -x "$POETRY_EXEC" ]];then
    RUN_PREFIX="$POETRY_EXEC run";
else
    # run directly -- note deps must be pre-installed on system
    RUN_PREFIX="";
fi

# get current (epoch-) time in seconds
DATE=`date +%s`
# round to last N seconds + offset
(( DATE /= $CRON_SECONDS, DATE *= 300, DATE += $CRON_OFFSET_SECONDS ))

PROJECT_DIR="`dirname $0`/.."
EXEC="$RUN_PREFIX python -m tootroll -u -l 800"

# run
cd "$PROJECT_DIR"/src && \
    STATS=`$EXEC |sed 's/[_a-z=]*//g'` && \
    echo $DATE,$STATS || exit_on_fail "run failed, exiting..."
exit 0
