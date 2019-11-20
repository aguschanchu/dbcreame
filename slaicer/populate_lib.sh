#!/bin/bash

if [ -f lib ]; then
    echo "lib folder already exists! deleting"
    rm -rf lib
fi
mkdir lib
cd lib

# buildtools
sudo apt-get install -y build-essential git python3-pip libssl-dev libffi-dev python3-dev redis-server default-libmysqlclient-dev mysql-client
sudo apt-get install -y cpanminus liblocal-lib-perl libwxgtk-media3.0-dev htop cmake pkg-config libtbb-dev curl libcurl4-openssl-dev
sudo apt-get install -y libeigen3-dev libglew-dev libglewmx-dev cpanminus

# Tweaker3
git clone https://github.com/ChristophSchranz/Tweaker-3/

# Slic3r PE
git clone https://github.com/prusa3d/Slic3r
cd Slic3r
sudo apt-get build-dep -y slic3r
git checkout origin/stable
mkdir build
cd build
cmake .. && make -j1