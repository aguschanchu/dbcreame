import subprocess
from django.conf import settings

def convert_stl_to_sfb(fieldfile):
    #Convertimos el STL a OBJ
    obj_path = settings.BASE_DIR + '/tmp/' + fieldfile.name.split('/')[-1].split('.')[0] + '.obj'
    args = ['assimp', 'export', settings.BASE_DIR+fieldfile.url, obj_path]
    proc = subprocess.run(args,universal_newlines = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    #Se convirtio exitosamente?
    if 'Exporting file ...                   OK ' not in proc.stdout.splitlines():
        raise Exception("Error al convertir STL a OBJ")
        print(proc.stdout.splitlines())
    #Convertimos el sfb
    args = [settings.BASE_DIR + '/lib/sceneform_sdk/linux/converter','-d','--mat',settings.BASE_DIR + '/lib/sceneform_sdk/default_materials/obj_material.sfm',
    '--outdir', settings.BASE_DIR + '/tmp/',obj_path]
    proc = subprocess.run(args,universal_newlines = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    #TODO: reecalar el modelo, *1/1000
    print(proc.stdout.splitlines())
    print(proc.stderr.splitlines())
