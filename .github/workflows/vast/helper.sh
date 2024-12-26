#!/bin/bash

ARG=$1
if [ "$ARG" = "create" ]; then

  VAST_API_KEY=$2

  echo "helper: priovision..."
  bash .github/workflows/vast/provision.sh $VAST_API_KEY

  echo "helper: transfer..."
  bash /tmp/vast-ci/rsync-command.sh

  echo "helper: warmup..."
  bash .github/workflows/vast/run.sh warmup

  echo "helper: build..."
  bash .github/workflows/vast/run.sh build

  echo "helper: convert..."
  bash .github/workflows/vast/run.sh convert

elif [ "$ARG" = "run" ]; then

  SCRIPT_NAME=$2

  echo "helper: run..."
  bash .github/workflows/vast/run.sh run $SCRIPT_NAME

elif [ "$ARG" = "delete" ]; then

  echo "helper: delete..."
  bash /tmp/vast-ci/delete-instance.sh

fi
