from django.db import models
import uuid

class EscaneoManager(models.Manager):
    '''
    La idea es crear el trabajo, y las imagenes con los nombres indicados inicialmente. De este modo, si alguna transferencia
    se realiza en forma incorrecta, podemos identificarla
    '''
    def create_object(self, amount, name_list=None):
        #Podemos pasar una lista de nombres, o generarla como una lista
        if not name_list:
            name_list = [str(a)+'.jpeg' for a in range(0, amount)]
        #Creamos la instancia de Escaneo, y guardamos la lista de archivos
        scan = Escaneo.objects.create()
        for name in name_list:
            Identificador.objects.create(job=scan, name=name)

        return scan

class Escaneo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    objects = EscaneoManager()

    @property
    def remaining_files(self):
        return [x.name for x in self.filenames.all() if not Imagen.objects.filter(job=self, original_filename=x.name).exists()]

class Identificador(models.Model):
    name = models.CharField(max_length=300)
    job = models.ForeignKey(Escaneo, on_delete=models.CASCADE, related_name='filenames')

class Imagen(models.Model):
    job = models.ForeignKey(Escaneo, on_delete=models.CASCADE, related_name='images')
    photo = models.ImageField(null=True)
    original_filename = models.CharField(max_length=300)
