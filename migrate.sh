rm -r db/migrations media tmp
mkdir media tmp
mkdir media/images media/renders media/sfb media/stl
mkdir media/images/plots
#PSQL DB preparation
sudo -u postgres -H -- psql -c "DROP DATABASE dbapi"
sudo -u postgres -H -- psql -c "CREATE USER dbapi WITH PASSWORD '***REMOVED***'"
sudo -u postgres -H -- psql -c "DROP DATABASE dbapi"
sudo -u postgres -H -- psql -c "CREATE DATABASE dbapi"
sudo -u postgres -H -- psql -c "ALTER ROLE dbapi SET client_encoding TO 'utf8'"
sudo -u postgres -H -- psql -c "ALTER ROLE dbapi SET default_transaction_isolation TO 'read committed'"
sudo -u postgres -H -- psql -c "ALTER ROLE dbapi SET timezone TO 'UTC'"
sudo -u postgres -H -- psql -c "GRANT ALL PRIVILEGES ON DATABASE dbapi TO dbapi"
#DB population
python manage.py makemigrations db && python manage.py migrate && python populate.py
