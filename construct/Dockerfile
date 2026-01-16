FROM ubuntu:20.04

RUN apt-get update && apt-get install -y \
    build-essential \
    kmod \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app
