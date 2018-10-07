#!/usr/bin/env bash

export DJANGO_SETTINGS_MODULE="dbcreame.settings"

celery purge -A dbcreame -f && celery worker -A dbcreame -l info --concurrency=50 2>&1 | tee celery.log
