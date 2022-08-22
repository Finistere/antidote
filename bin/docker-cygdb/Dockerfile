FROM ubuntu:22.04

ENV TZ=Etc/UTC
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get -y install --no-install-recommends ca-certificates build-essential libreadline-dev libncursesw5-dev libssl-dev libsqlite3-dev tk-dev libgdbm-dev libc6-dev libbz2-dev libffi-dev zlib1g-dev git wget gcc g++ gdb libc++-dev


ARG USER_NAME
ARG USER_ID
ARG GROUP_ID
ARG HOME

RUN if getent group $GROUP_ID ; then \
        GROUP="$(getent group $GROUP_ID | cut -d: -f1)"; \
    else \
        groupadd -g $GROUP_ID $USER_NAME; \
        GROUP=$USER_NAME; \
    fi &&\
    if ! getent passwd $USER_ID >/dev/null 2>&1; then \
        useradd -l -u $USER_ID -g $GROUP $USER_NAME &&\
        install -d -m 0755 -o $USER_NAME -g $GROUP $HOME; \
    fi

# Switch to user to write with correct permissions in the project.
USER $USER_NAME

RUN wget -P ~ https://git.io/.gdbinit &&\
    git config --global --add safe.directory /antidote &&\
    wget -P /tmp https://www.python.org/ftp/python/3.10.6/Python-3.10.6.tar.xz &&\
    cd /tmp && tar -Jxf Python-3.10.6.tar.xz

RUN cd /tmp/Python-3.10.6 &&\
    ./configure --prefix /tmp/Python --with-trace-refs --with-pydebug &&\
    make install -j16
