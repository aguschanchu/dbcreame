from django.conf import settings
import numpy as np
import json
import urllib3
from urllib3.util import Retry
from urllib3 import PoolManager, ProxyManager, Timeout
from urllib3.exceptions import MaxRetryError, TimeoutError
urllib3.disable_warnings()


from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)


def get_connection_pool():
    retry_policy = Retry(total=5, backoff_factor=0.1, status_forcelist=list(range(405,501)))
    timeout_policy = Timeout(read=10, connect=5)
    http = PoolManager(retries= retry_policy, timeout = timeout_policy)

    return http

def segundos_a_pesos(segs):
    horas_de_impresion = segs/3600
    hora_base = settings.PRECIO_POR_HORA_DE_IMPRESION
    precio = (20*horas_de_impresion+5*min(horas_de_impresion,5)+5*min(horas_de_impresion,15)+5*min(horas_de_impresion,25)+5*min(horas_de_impresion,35))
    #Aplicamos el descuento en volumen precio_c_descuento = a*(precio_sin_descuento)^b
    return precio

def get_shipping_price(compra):
    if compra.delivery_address.postal_code is None:
        compra.delivery_address.update_long_address_and_postal_code()
    try:
        http = get_connection_pool()
        r = json.loads(http.request('GET', settings.SHIPNOW_API_URL.format(zip=compra.delivery_address.postal_code)).data.decode('utf-8'))
        return r['price']
    except:
        return 200

def get_order_price(compra):
    total_price = 0
    print(compra)
    for objeto_personalizado in compra.purchased_objects.all():
        object_total_seconds = 0
        if objeto_personalizado.scale == 1:
            object_total_seconds = objeto_personalizado.object_id.printing_time_default_total()
        else:
            #Usamos el polinomio para calcular el tiempo de impresion de cada objeto
            for archivostl in objeto_personalizado.object_id.files.all():
                p = np.poly1d(archivostl.time_as_a_function_of_scale.coefficients_list())
                print(archivostl.time_as_a_function_of_scale.coefficients_list())
                object_total_seconds += p(objeto_personalizado.scale)
        total_price += segundos_a_pesos(object_total_seconds) * objeto_personalizado.quantity * objeto_personalizado.object_id.discount
    return total_price - total_price % 5

def obtener_parametros_de_precios():
    return {'price_per_hour' : settings.PRECIO_POR_HORA_DE_IMPRESION,
    'discount_parameter_a' : settings.PRECIO_DESCUENTO_VOLUMEN_A,
    'discount_parameter_b' : settings.PRECIO_DESCUENTO_VOLUMEN_B}
