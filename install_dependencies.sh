#!/usr/bin/env bash

cd $HOME
# Install git
yum install -y git libtool gcc-c++
yum install -y m4

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
yum install -y boost-devel

# Install libtins dependencies
yum install -y libpcap-devel openssl-devel cmake

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

