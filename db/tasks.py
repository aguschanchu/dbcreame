from __future__ import absolute_import
from celery import shared_task, chord, group
from db import models as modelos
from django_mercadopago import models as MPModels
from django.conf import settings

#Pregunta a MP por el estado de un pago
@shared_task(autoretry_for=(ValueError,), max_retries=20, retry_backoff=True, retry_backoff_max=24*60**2)
def query_mp_for_payment_status(preference_id):
    preference = MPModels.Preference.objects.get(pk=preference_id)
    #Actualizamos el estado de la preferencia
    preference.poll_status()
    ##Estamos en modo sandbox? De ser asi, la marcamos automaticamente como pagada
    if settings.MERCADOPAGO_SANDBOX_MODE:
        preference.paid = True
        preference.save()
    #Ya deberiamos tener la preferencia actualizada. Si no fue paga, entramos en excepcion
    #de este modo, se comprobara al cabo de un tiempo si fue pagada
    if not preference.paid:
        raise ValueError("Preferencia no paga. Reintentando")
