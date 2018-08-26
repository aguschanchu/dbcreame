rm -r db/migrations media tmp
mkdir media tmp
mkdir media/images media/renders media/sfb media/stl
python manage.py makemigrations db && python manage.py migrate && python populate.py
