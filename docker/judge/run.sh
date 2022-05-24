#!/usr/bin/env bash

set -eux

if [[ $WLMOJ_JUDGE_MODE == *"demo"* ]]; then
  ls /opt/wlmoj_judge/problems-init
  cp -r /opt/wlmoj_judge/problems-init/aplusb /opt/wlmoj_judge_problem_storage/
fi

export DMOJ_IN_DOCKER=1
export PYTHONUNBUFFERED=1
export LANG=C.UTF-8
export PYTHONIOENCODING=utf8

cd /judge

cat /opt/wlmoj_judge/config.yml

runuser -u judge 'dmoj' -- \
  -p "$BRIDGED_JUDGE_PORT" \
  -c '/opt/wlmoj_judge/config.yml' \
  "$BRIDGED_JUDGE_HOST" \
  "$JUDGE_NAME" \
  "$JUDGE_KEY"
