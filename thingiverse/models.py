from django.db import models
import datetime

'''
Tenemos un limite de 300/5', queremos monitorear cada key, para no pasarnos
'''

class QueryEvent(models.Model):
    date = models.DateTimeField(auto_now_add=True)

class ApiKey(models.Model):
    quota = 290
    quota_interval = 5*60
    key = models.CharField(max_length=100)
    meter = models.ManyToManyField(QueryEvent)

    def clean(self):
        #¿Es valida?
        r = requests.get(settings.THINGIVERSE_API_ENDPOINT+'things/763622?access_token='+str(self.key)).json()
        if 'Unauthorized' in r.values():
            raise ValidationError('API key invalida')

    def make_query(self):
        event = QueryEvent.objects.create()
        self.meter.add(event)

    def available(self, count=1):
        #Actualizamos la tabla de meters:
        for event in self.meter.all():
            if (datetime.datetime.now(datetime.timezone.utc)-event.date).seconds > self.quota_interval:
                event.delete()
        if len(self.meter.all()) + count <= self.quota:
            return True
        else:
            return False

    @staticmethod
    def get_api_key(count=1):
        for key in ApiKey.objects.all():
            if key.available(count):
                for _ in range(0,count):
                    key.make_query()
                return key.key
            else:
                return None
