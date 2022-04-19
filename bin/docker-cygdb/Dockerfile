FROM ubuntu:22.04

RUN apt-get update &&\
    apt-get install --no-install-recommends -y python3 python3-dev python3-dbg python3-virtualenv git wget gcc g++ gdb

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
    git config --global --add safe.directory /antidote
