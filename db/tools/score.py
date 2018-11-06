
'''
La idea es ordenar los puntajes por popularidad, para darle al usuario resultados mas relevantes.
Esta en un apartado, ya que, esto puede volverse muy complejo con el tiempo
'''
def score_object(obj, usuario = None):
    score = 0

    #Likes propios
    score += obj.like_count * 100

    #En caso que tenga un repositorio externo, usamos esa informacion
    if obj.external_id != None:
        if obj.external_id.repository == 'thingiverse':
            score += obj.external_id.thingiverse_attributes.like_count

    return score
