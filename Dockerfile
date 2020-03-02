FROM nvidia/cuda:10.1-base-ubuntu18.04

ENV NVIDIA_DRIVER_CAPABILITIES=video,compute,utility

ENV TZ=Europe/Minsk
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt update && apt install software-properties-common -y
RUN add-apt-repository ppa:deadsnakes/ppa

RUN apt-get update && apt-get install -y \
    python3.7 \
    python3-pip \
    htop \
    apt-utils \
    wget \
    git \
    curl \
    nano \
    locales \
    build-essential \
    libssl-dev \
    unzip \
    libtool \
    automake \
    pkg-config \
    libfftw3-dev \
    ffmpeg \
    && apt-get clean && rm -rf /var/lib/apt/lists/*



RUN pip3 install ffmpeg-python tinydb psutil

RUN python3.7 --version

ADD . /app/
WORKDIR /app
CMD ["python3", "server.py"]