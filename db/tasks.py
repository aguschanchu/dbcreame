from __future__ import absolute_import
from celery import shared_task, chord, group
from db.models import Compra
from django_mercadopago import models as MPModels
from django.conf import settings

#Pregunta a MP por el estado de un pago
@shared_task(autoretry_for=(ValueError,), max_retries=20, retry_backoff=True, retry_backoff_max=24*60**2)
def query_mp_for_payment_status(compra_id):
