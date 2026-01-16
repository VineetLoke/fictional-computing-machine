FROM kalilinux/kali-rolling:latest

# Install Must-Have Tools
RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    vim \
    nmap \
    metasploit-framework \
    python3 \
    python3-pip \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set default shell to bash
SHELL ["/bin/bash", "-c"]
