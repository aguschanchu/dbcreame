#!/usr/bin/env bash

export DJANGO_SETTINGS_MODULE="dbcreame.integration_testing"

celery purge -A dbcreame -f && celery worker -A dbcreame -l info
