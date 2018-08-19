import subprocess
from django.conf import settings
from django.db import models
import numpy as np
import trimesh
import os
import traceback

def convert(fieldfile):
    '''
    El proceso de conversion a sfb consiste en
    1) Reescalar el stl con un factor 1/1000, ya que sfb asume que las unidades de los modelos están en metros
    mientras todo thingiverse labura con mm. Utilizamos trimesh para tal tarea
    2) Convertir STL a OBJ
    3) Convertir OBJ a SFB
    '''
    #Reescalamos el STL
    stlpath = settings.BASE_DIR+fieldfile.url
    try:
        mesh = trimesh.load_mesh(stlpath)
    except:
        traceback.print_exc()
        print(stlpath)
        raise Exception("Error al importar STL a trimesh")
    t = trimesh.transformations.scale_matrix(1/1000, [0,0,0])
    mesh.apply_transform(t)
    #Guardamos el OBJ
    obj_path = settings.BASE_DIR + '/tmp/' + fieldfile.name.split('/')[-1].split('.')[0] + '.obj'
    with open(obj_path,'w') as f:
        f.write(trimesh.io.wavefront.export_wavefront(mesh))
    #Convertimos el sfb
    args = [settings.BASE_DIR + '/lib/sceneform_sdk/linux/converter','-d','--mat',settings.BASE_DIR + '/lib/sceneform_sdk/default_materials/obj_material.sfm',
    '--outdir', settings.BASE_DIR + '/tmp/',obj_path]
    proc = subprocess.run(args,universal_newlines = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    os.remove(obj_path)
    #Se proceso correctamente?
    if 'Wrote SFB to' not in proc.stdout.splitlines()[1]:
        raise Exception("Error al exportar SFB")
    #Devolvemos el path del sfb
    return settings.BASE_DIR + '/tmp/' + fieldfile.name.split('/')[-1].split('.')[0] + '.sfb'

def combine_stls_files(objeto):
    '''
    Combina los distintos STLs en un unico STL, ubicados de modo que los modelos no se intersequen entre ellos, y que el rectangulo
    que los contiene sea del menor tamaño posible. La idea, es ofrecer este STL como alternativa al "STL combinado" para AR,
    en caso de que este no haya sido generado aun.
    '''
    build_plate_size = 200
    arrange_completed = False
    args = [settings.BASE_DIR + '/lib/simarrange/simarrange']
    for archivo_stl in objeto.files.all():
        args.append(settings.BASE_DIR+archivo_stl.file.url)
    #Buscamos build_plate_size minimo
    while not arrange_completed:
        args_d = args.copy() + ['--dryrun','-x',str(build_plate_size),'-y',str(build_plate_size),'--spacing',str(10)]
        proc = subprocess.run(args_d,universal_newlines = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        #Entro todo?
        print(build_plate_size)
        for line in proc.stdout.splitlines():
            print(line)
            if "Generating plate 1" in line or 'SKIP' in line:
                build_plate_size += 50
                break
            if "Could not fit this file as the first item of the plate in any tested orientation! It might be too large for the print area." in line:
                build_plate_size += 50
                break
        else:
            args_d = args.copy() + ['-x',str(build_plate_size),'-y',str(build_plate_size),'--spacing',str(10),'--outputdir',settings.BASE_DIR+'/tmp/'+str(objeto.name)+'/']
            os.mkdir(settings.BASE_DIR+'/tmp/'+str(objeto.name))
            proc = subprocess.run(args_d,universal_newlines = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE,cwd=settings.BASE_DIR+'/tmp/'+str(objeto.name)+'/')
            return settings.BASE_DIR+'/tmp/'+str(objeto.name)
