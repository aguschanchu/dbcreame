#!/usr/bin/env bash

export DJANGO_SETTINGS_MODULE="dbcreame.settings"

celery purge -A dbcreame -f
celery worker -A dbcreame -l info -Q http -P eventlet -c 500 -n httpworker@%h &
celery worker -A dbcreame -l info --concurrency=50 -Q celery -n celery@%h 2>&1 | tee celery.log
