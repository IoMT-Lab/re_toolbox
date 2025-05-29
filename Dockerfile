FROM rust:latest

RUN apt-get update \
    && apt-get install -y apt-transport-https gpg \
    && wget -qO - https://packages.adoptium.net/artifactory/api/gpg/key/public | gpg --dearmor | tee /etc/apt/trusted.gpg.d/adoptium.gpg > /dev/null \
    && echo "deb https://packages.adoptium.net/artifactory/deb $(awk -F= '/^VERSION_CODENAME/{print$2}' /etc/os-release) main" | tee /etc/apt/sources.list.d/adoptium.list \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update \
    && apt-get install -y \
        clang-format \
        temurin-21-jdk \
        idle \
    && rm -rf /var/lib/apt/lists/*

ADD Python-3.12.10.tar.xz /python
WORKDIR /python/Python-3.12.10
RUN ./configure --enable-optimizations \
    && make \
    && make altinstall \ 
    && /usr/local/bin/pip3.12 install pipenv

RUN apt-get update \
    && apt-get update \
    && apt-get install -y \
        clang-format \
        temurin-21-jdk \
    && rm -rf /var/lib/apt/lists/*

RUN /usr/local/bin/pip3.12 install --break-system-packages angr
COPY . /app
WORKDIR /app
RUN cargo build

RUN cd tools/comcat && pipenv install
RUN cd tools/demangle && pipenv install
RUN cd tools/degpt && pipenv install

ENV PLUGIN_PATH=/app/plugins
ENV GHIDRA_DIR=/app/tools/ghidra
ENV ANGR_DIR=/app/tools/angr
ENV CHAT_GPT_API_KEY="YOUR KEY HERE"

CMD [ "/bin/bash", "-c", "/app/target/debug/re_toolbox" ]