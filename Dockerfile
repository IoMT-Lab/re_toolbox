# syntax=docker/dockerfile:1
FROM rust:slim-bookworm

RUN apt-get update \
    && apt-get install -y apt-transport-https gpg wget \
    && wget -qO - https://packages.adoptium.net/artifactory/api/gpg/key/public | gpg --dearmor | tee /etc/apt/trusted.gpg.d/adoptium.gpg > /dev/null \
    && echo "deb https://packages.adoptium.net/artifactory/deb $(awk -F= '/^VERSION_CODENAME/{print$2}' /etc/os-release) main" | tee /etc/apt/sources.list.d/adoptium.list \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    ca-certificates \
    idle \
    temurin-21-jdk\
    clang-format \
    # KLEE + Z3 system dependencies & build tools
    build-essential \
    cmake \
    curl \
    file \
    g++-multilib \
    gcc-multilib \
    git \
    unzip \
    libcap-dev \
    libgoogle-perftools-dev \
    libncurses-dev \
    libsqlite3-dev \
    libtcmalloc-minimal4 \
    graphviz \
    doxygen \
    clang-15 \
    llvm-15 \
    llvm-15-dev \
    llvm-15-tools \
    gcc-arm-none-eabi \
    binutils-arm-none-eabi \
    zlib1g-dev \ 
    libssl-dev \
    libbz2-dev \
    && rm -rf /var/lib/apt/lists/*

ADD Python-3.12.10.tar.xz /python
WORKDIR /python/Python-3.12.10
RUN ./configure --enable-optimizations \
    && make \
    && make altinstall \ 
    && /usr/local/bin/pip3.12 install pipenv

RUN /usr/local/bin/pip3.12 install --break-system-packages angr lit wllvm tabulate networkx scipy matplotlib

ADD --unpack=true https://github.com/avast/retdec/releases/download/v5.0/RetDec-v5.0-Linux-Release.tar.xz /retdec

# --- Building KLEE and dependencies from source ---

# Stage 3: Build and install Z3 from source
WORKDIR /tmp/build_z3_src
RUN git clone --depth 1 --branch z3-4.15.4 https://github.com/Z3Prover/z3.git . && \
    python3 scripts/mk_make.py && \
    cd build && \
    make -j$(nproc) && \
    make install && \
    # Clean up the build directory
    rm -rf /tmp/build_z3_src

# Stage 4: Build klee-uclibc from source and move to a persistent location
WORKDIR /tmp/build_klee_uclibc_src
RUN git clone https://github.com/klee/klee-uclibc.git . && \
    chmod -R +x . && \
    ./configure --make-llvm-lib --with-cc=clang-15 --with-llvm-config=llvm-config-15 && \
    make -j$(nproc) && \
    # Move built klee-uclibc to /opt for KLEE to find
    mkdir -p /opt/klee-uclibc-built && \
    cp -R ./* /opt/klee-uclibc-built/ && \
    # Clean up the temporary build directory
    rm -rf /tmp/build_klee_uclibc_src

# KLEE will be configured with -DKLEE_UCLIBC_PATH=/opt/klee-uclibc-built

# Stage 5: Copy googletest source to a persistent location
# KLEE's unit tests require the googletest source directory.
RUN mkdir -p /opt && cd /opt && \
    curl -L https://github.com/google/googletest/archive/release-1.11.0.zip -o googletest.zip && \
    unzip googletest.zip && \
    rm googletest.zip && \
    mv googletest-release-1.11.0 googletest-source
# KLEE will be configured with -DGTEST_SRC_DIR=/opt/googletest-source/googletest
# (assuming 'googletest' is the subdirectory within your source_googletest folder that contains CMakeLists.txt for gtest)
# If your source_googletest *is* the googletest directory itself, then use /opt/googletest-source

# Stage 6: Build and install KLEE from source
WORKDIR /tmp/build_klee_src
RUN git clone https://github.com/klee/klee.git . && \
    mkdir build && cd build && \
    cmake \
    -DENABLE_SOLVER_STP=OFF \
    -DENABLE_POSIX_RUNTIME=ON \
    -DENABLE_UNIT_TESTS=ON \
    -DKLEE_UCLIBC_PATH=/opt/klee-uclibc-built \
    -DGTEST_SRC_DIR=/opt/googletest-source \
    -DLLVM_DIR=/usr/lib/llvm-15/lib/cmake/llvm \
    -Dgtest_build_tests=OFF \
    # Add any other KLEE cmake options you need
    .. && \
    make -j$(nproc) && \
    make install && \
    # Clean up the build directory
    rm -rf /tmp/build_klee_src
# --- End of Building KLEE and dependencies ---

# Stage 7: Application setup - copy your project and install Pipfile dependencies

COPY . /app
WORKDIR /app
RUN cargo build

ENV PIPENV_VENV_IN_PROJECT=1
RUN cd tools/angr && pipenv install
RUN cd tools/comcat && pipenv install
RUN cd tools/demangle && pipenv install
RUN cd tools/degpt && pipenv install
RUN cd tools/typeinfer/trex && cargo install --path . && pipenv install
RUN cd tools/ai_decomp && /usr/local/bin/pip3.12 install --break-system-packages -r requirements.txt
RUN cd tools/agent4decompile && pipenv install

ENV PLUGIN_PATH=/app/plugins
ENV GHIDRA_DIR=/app/tools/ghidra
ENV GHIDRA_PATH=${GHIDRA_DIR}/ghidra_11.4.2_PUBLIC
ENV RETDEC_PATH=/retdec/bin/retdec-decompiler
ENV ANGR_DIR=/app/tools/angr
ENV TREX_PATH=/app/tools/typeinfer/trex/target/release/trex
ENV AI_DECOMP_PATH=/app/tools/ai_decomp/decomp/decompile.py
ENV CHAT_GPT_API_KEY="YOUR KEY HERE"
ENV DEEPSEEK_API_KEY="YOUR OTHER KEY HERE"
ENV OPENAI_API_KEY=${CHAT_GPT_API_KEY}

RUN ln -s /usr/local/bin/python3.12 /usr/local/bin/python3
CMD [ "/bin/bash", "-c", "/app/target/debug/re_toolbox" ]