#!/usr/bin/env bash
#Basado en Debian 9
cd
sudo apt-get update && sudo apt-get upgrade
sudo apt-get install -y build-essential git
git clone http://agus@outreach.agusc.com.ar:7990/scm/cre3d/dbcreame.git
sudo apt-get install python3-pip libssl-dev libffi-dev python3-dev redis-server default-libmysqlclient-dev mysql-client mysql-server
#venv usa python3.5, el default de debian. Por eso, bajo Anaconda
wget https://repo.anaconda.com/archive/Anaconda3-2019.03-Linux-x86_64.sh
chmod +x Anaconda3-2019.03-Linux-x86_64.sh
sh Anaconda3-2019.03-Linux-x86_64.sh
export PATH="/home/agus/anaconda3/bin:$PATH"
cd dbcreame
git checkout develop
sh migrate.sh
cd slaicer
sh populate_lib.sh
cd ..

#Listo el slicer, seteamos Python
pip install wheel
conda install -c conda-forge uwsgi libiconv
pip install -r requirements.txt

# Localenv config
printf '%s\n' "CURRENT_HOST = 'api.creame3d.com'" "CURRENT_PROTOCOL = 'https'" "CURRENT_PORT = 443" "USE_SCAPOXY = False" > dbcreame/localenv.py

# Systemd service config
sudo bash -c "cat <<EOF > /etc/systemd/system/slaicer.service
[Unit]
Description=celery instance of slaicer
After=network.target

[Service]
User=agus
Group=agus
WorkingDirectory=/home/agus/dbcreame
Environment='PATH=/home/agus/anaconda3/bin:/usr/local/bin:/usr/bin:/bin'
ExecStart=/home/agus/anaconda3/bin/celery -A dbcreame worker -l info -E -Ofair -Q slaicer --concurrency=2 -n slaicer@%%h

[Install]
WantedBy=multi-user.target
EOF"
sudo ln -s /etc/systemd/system/multi-user.target.wants/slaicer.service /etc/systemd/system/slaicer.service