from django.conf import settings
import numpy as np

def segundos_a_pesos(segs):
    horas_de_impresion = segs/3600
    hora_base = settings.PRECIO_POR_HORA_DE_IMPRESION
    precio = (20*horas_de_impresion+5*min(horas_de_impresion,5)+5*min(horas_de_impresion,15)+5*min(horas_de_impresion,25)+5*min(horas_de_impresion,35))
    #Aplicamos el descuento en volumen precio_c_descuento = a*(precio_sin_descuento)^b
    return precio

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
