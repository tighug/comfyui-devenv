FROM nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04

ENV TZ=Asia/Tokyo
ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_ROOT_USER_ACTION=ignore
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    exa \
    ffmpeg \
    git \
    python3-dev \
    python3-pip \
    python3-tk \
    libopencv-dev \
    make \
    tzdata \
    vim \
    wget \
    zsh
RUN sh -c "$(curl -fsSL https://starship.rs/install.sh)" -y -f
RUN apt-get autoremove -y
