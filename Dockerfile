FROM quay.io/fedora/python-312:latest
MAINTAINER https://github.com/SatelliteQE

ENV PYCURL_SSL_LIBRARY=openssl \
    ROBOTTELO_DIR="${HOME}/robottelo"

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

USER 1001
COPY --chown=1001:0 / ${ROBOTTELO_DIR}

WORKDIR "${ROBOTTELO_DIR}"
RUN uv pip install -r requirements.txt

CMD make test-robottelo
