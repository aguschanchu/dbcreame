from django.conf import settings

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
