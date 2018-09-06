from django.conf import settings
import numpy as np

def segundos_a_pesos(segs):
    horas_de_impresion = segs/3600
    hora_base = settings.PRECIO_POR_HORA_DE_IMPRESION
    if horas_de_impresion < 5:
        return horas_de_impresion*hora_base
    elif horas_de_impresion < 15:
        return ((horas_de_impresion-5)*0.875+5)*hora_base
    elif horas_de_impresion < 25:
        return ((horas_de_impresion-15)*0.75+5+10*0.875)*hora_base
    elif horas_de_impresion < 35:
        return ((horas_de_impresion-25)*0.625+5+10*0.875+10*0.75)*hora_base
    else:
        return ((horas_de_impresion-35)*0.5+5+10*0.875+10*0.75+10*0.625)*hora_base

def get_order_price(compra):
    total_price = 0
    print(compra)
    for objeto_personalizado in compra.purchased_objects.all():
        object_total_seconds = 0
        if objeto_personalizado.scale == 1:
            object_total_seconds = objeto_personalizado.object_id.printing_time_default_total()
            #Usamos el polinomio para calcular el tiempo de impresion de cada objeto
        else:
            for archivostl in objeto_personalizado.object_id.files.all():
                p = np.poly1d(archivostl.time_as_a_function_of_scale.coefficients_list())
                print(archivostl.time_as_a_function_of_scale.coefficients_list())
                object_total_seconds += p(objeto_personalizado.scale)
        total_price += segundos_a_pesos(object_total_seconds) * objeto_personalizado.quantity
    return total_price
