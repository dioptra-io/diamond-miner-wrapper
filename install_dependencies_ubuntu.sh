#!/usr/bin/env bash

cd $HOME
# Install git
apt-get install -y git libtool g++ autoconf
apt-get install -y m4

# Install libcperm
cd $HOME
git clone https://github.com/lancealt/libcperm
cd libcperm
./autogen.sh
./configure
make
make install
cd $HOME

# Install boost
apt-get install -y libboost-all-dev

# Install libtins dependencies
apt-get install -y libpcap-dev libssl-dev cmake

# Install libtins

git clone https://github.com/mfontanini/libtins.git
cd libtins
mkdir build
cd build
cmake ../ -DLIBTINS_ENABLE_CXX11=1
make
make install
cd $HOME
ldconfig

# We're in home

