from db.models import Objeto

def name_in_name(thing: Objeto):
    # Sort thing files by name
    thing_files = list(thing.files.all())
    thing_files.sort(key=lambda x: len(x.informacionthingi.original_filename), reverse=False)

    name_list = [x.informacionthingi.original_filename.split('.')[0].lower() for x in thing_files]
    for i in range(len(thing_files)):
        for j in range(i+1, len(thing_files), 1):
            if thing_files[i].informacionthingi.original_filename.split('.')[0].lower() in name_list[j]:
                ti = thing_files[i].informacionthingi
                ti.filter_passed = False
                ti.save()

