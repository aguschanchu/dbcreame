rm -r db.sqlite3 db/migrations
python manage.py makemigrations db && python manage.py migrate && python populate.py
