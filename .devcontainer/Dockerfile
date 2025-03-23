FROM nvidia/cuda:12.1.0-cudnn8-devel-ubuntu22.04

ENV TZ=Asia/Tokyo
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    exa \
    git \
    python3-pip \
    python3-dev \
    libopencv-dev \
    make \
    tzdata \
    vim \
    zsh
RUN sh -c "$(curl -fsSL https://starship.rs/install.sh)" -y -f
RUN apt-get autoremove -y
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
RUN pip install ninja
RUN pip install torch torchvision torchaudio
