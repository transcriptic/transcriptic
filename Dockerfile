FROM debian:jessie

MAINTAINER Transcriptic <engineering@strateos.com>

# Default userid=1000 as that is the first non-root userid on linux
ARG uid=1000

RUN DEBIAN_FRONTEND=noninteractive apt-get update && apt-get install -y \
	python-dev \
	python \
	python-pip \
	python3-pip \
	python-virtualenv \
	python-setuptools \
	libfreetype6-dev \
    libpng12-0-dev \
    libjpeg-dev \
	pkg-config \
	libblas-dev \
	liblapack-dev \
	gfortran \
	wget \
	git \
	&& rm -rf /var/lib/apt/lists/*


# Change default install directory of pip
RUN mkdir /pip_cache
ENV XDG_CONFIG_HOME /pip_cache

# Change default install directory of eggs
RUN mkdir /python_eggs
ENV PYTHON_EGG_CACHE /python_eggs

# Upgrade pip and virtualenv to enable wheels
RUN pip install -U pip virtualenv setuptools
RUN pip3 install -U pip

# Install TxPy for Python2
RUN pip install transcriptic

# Install TxPy for Python3
RUN pip3 install transcriptic

# Install test dependencies
RUN pip install tox pytest

# Add user txpy with specified uid
RUN useradd -u $uid -m -s /bin/bash txpy
ENV HOME /home/txpy
WORKDIR /home/txpy

RUN chown -R txpy /home/txpy
USER txpy
