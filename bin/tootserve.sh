#!/bin/bash

# This script serves the toots in (Parquet) database over HTTP.
#
# prerequisites:
# 0. install dependencies: poetry update
# 1. configure server: python -m tootroll --configure
#
# Example
# cd ${REPO_DIRECTORY} && bash bin/tootserve.sh
#
# Test
# curl "http://localhost:5000/api/v1/servers"

PROFILE="private"

exit_on_fail() { echo $1; exit 1;}
ctrl_c () { echo "Exiting..."; exit 0;}

trap ctrl_c INT


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

PROJECT_DIR="`dirname $0`/.."
EXEC="$RUN_PREFIX python -m tootroll --profile $PROFILE --web"

# run
cd "$PROJECT_DIR"/src || exit_on_fail "cant cd into ${PROJECT_DIR}/src"

# run forever -- exit via ctrl+c
while :
do
    $EXEC || sleep 1
done

exit 0
