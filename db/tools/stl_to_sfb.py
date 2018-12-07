import subprocess
from django.conf import settings
from django.db import models
import numpy as np
import trimesh
import os
import traceback
from django.core.files.base import ContentFile
import random, string
import gc

def convert(stlpath,name,rotate=False):
    '''
    El proceso de conversion a sfb consiste en
    1) Reescalar el stl con un factor 1/1000, ya que sfb asume que las unidades de los modelos están en metros
    mientras todo thingiverse labura con mm. Utilizamos trimesh para tal tarea
    2) Convertir STL a OBJ
    3) Convertir OBJ a SFB
    '''
    #Reescalamos el STL
    try:
        mesh = trimesh.load_mesh(stlpath)
    except:
        traceback.print_exc()
        print(stlpath)
        raise Exception("Error al importar STL a trimesh")
    t = trimesh.transformations.scale_matrix(1/1000, [0,0,0])
    mesh.apply_transform(t)
    if rotate:
        t = trimesh.transformations.rotation_matrix(-np.pi/2, [1,0,0])
        mesh.apply_transform(t)
    #Guardamos el STL transformado
    stl_path = settings.BASE_DIR + '/tmp/' + name.split('/')[-1].split('.')[0] + '.stl'
    with open(stl_path,'wb') as f:
        f.write(trimesh.io.stl.export_stl(mesh))
    #Convertimos el stl a obj usando assimp
    obj_path = settings.BASE_DIR + '/tmp/' + name.split('/')[-1].split('.')[0] + '.obj'
    args = ['assimp', 'export', stl_path, obj_path]
    proc = subprocess.run(args,universal_newlines = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    #Se convirtio exitosamente?
    if 'Exporting file ...                   OK ' not in proc.stdout.splitlines():
        print(proc.stdout.splitlines())
        raise Exception("Error al convertir STL a OBJ")
    #Convertimos el sfb
    args = [settings.BASE_DIR + '/lib/sceneform_sdk/linux/converter','-d','--mat',settings.BASE_DIR + '/lib/sceneform_sdk/default_materials/obj_material.sfm',
    '--outdir', settings.BASE_DIR + '/tmp/',obj_path]
    proc = subprocess.run(args,universal_newlines = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    #Borramos los archivos generados
    os.remove(obj_path)
    os.remove(stl_path)
    os.remove(obj_path+'.mtl')
    #Se proceso correctamente?
    for line in proc.stdout.splitlines():
        if 'Wrote SFB to' in line:
            break
    else:
        raise Exception("Error al exportar SFB")
    #Devolvemos el path del sfb
    return settings.BASE_DIR + '/tmp/' + name.split('/')[-1].split('.')[0] + '.sfb'

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
            dir = settings.BASE_DIR+'/tmp/'+''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            args_d = args.copy() + ['-x',str(build_plate_size),'-y',str(build_plate_size),'--spacing',str(10),'--outputdir',dir+'/']
            os.mkdir(dir)
            proc = subprocess.run(args_d,universal_newlines = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE,cwd=dir+'/')
            for line in proc.stdout.splitlines():
                if 'Generating plate 0' in line:
                    break
            else:
                print("Error al acomodar las piezas para el modelo sfb")
                print(proc.stdout.splitlines())
                print(proc.stderr.splitlines())
            return dir

def combine_stl_with_correct_coordinates(objeto):
    '''
    Una vez que los archivos tienen un sistema coordenado en comun, unimos los archivos para generar el
    STL cominado
    '''
    meshes = [trimesh.load_mesh(settings.BASE_DIR + a.file.url) for a in objeto.object.files.all()]
    mesh = trimesh.util.concatenate(meshes)
    filename = objeto.object.name
    new_file = ContentFile(trimesh.io.stl.export_stl(mesh))
    return new_file
