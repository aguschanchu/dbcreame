#!/usr/bin/env bash
screen -dmS celery celery -A dbcreame worker -l info -E -Ofair -Q slaicer --concurrency=2 -n slaicer@%h