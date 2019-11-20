#!/usr/bin/env bash

export DJANGO_SETTINGS_MODULE="dbcreame.integration_testing"

celery purge -A dbcreame -f
celery worker -A dbcreame -l info -Q http -P eventlet -c 500 -n httpworker@%h &
celery worker -A dbcreame -l info --concurrency=3 -Q low_priority -n low_priority@%h &
celery worker -A dbcreame -l info --concurrency=20 -Q celery -n celery@%h 2>&1 | tee celery.log &
celery worker -A dbcreame -l info --concurrency=2 -Q slaicer-geom -n slaicer@%h &
celery worker -A dbcreame -l info --concurrency=1 -Q slaicer -n slaicer-geom@%h &
celery worker -A dbcreame -l info --concurrency=2 -Q visionapi -n visionapi@%h

