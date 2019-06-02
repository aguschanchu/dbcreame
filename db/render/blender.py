from django.conf import settings
import subprocess
import traceback
import random
import string
import os
'''
Crear scripts de Blender en función del ModeloAR pasado, y lo ejecuta
Guarda la imagen resultante en tmp/, y devuelve el resultado
'''

def render_image(armodel):
    script_dir = settings.BASE_DIR+'/tmp/'+''.join(random.choices(string.ascii_uppercase + string.digits, k=8))+'.py'
    output_png = settings.BASE_DIR+'/tmp/'+''.join(random.choices(string.ascii_uppercase + string.digits, k=8))+'.png'

    #Preparamos el script que ejecutara blender. Si, necesariamente hay que hacer esto, no puedo simplemente correr bpy desde aca
    with open(script_dir,'w') as dest:
        with open('db/render/blender_script_base.py','r') as source:
            for line in source.readlines():
                line = line.replace('MODEL_PATH',"'"+armodel.combined_stl.path+"'")
                line = line.replace('OUTPUT_PATH',"'"+output_png+"'")
                dest.write(line)
    #Corremos Blender
    args = [settings.BASE_DIR+'/lib/blender/blender','--python',script_dir,'--background']
    try:
        proc = subprocess.run(args,universal_newlines = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE,timeout=60*5)
    except subprocess.TimeoutExpired:
        raise Exception("Timeout al renderizar imagen")
    else:
        traceback.print_exc()
    for line in proc.stdout.splitlines():
         if 'Saved: ' in line:
             break
    else:
        print(proc)
        raise Exception("Error al renderizar imagen")
    #Borramos el script, y devolvemos la ruta de la imagen
    os.remove(script_dir)
    return output_png

'''
from db.models import *
m=Objeto.objects.all()[0].modeloar
from db.render.blender import render_image
render_image(m)

'''
