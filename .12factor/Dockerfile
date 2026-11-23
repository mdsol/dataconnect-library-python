# syntax=docker/dockerfile:experimental


#
# Stage 0) Arg defaults and base image
#
ARG POETRY_VERSION=2.3.4
ARG VENV_PATH="/tmp/venv"
ARG APP_HOME="/home/app"
ARG PACKAGE_GROUPS="main"

FROM mdsol-docker-prod-virtual.jfrog.io/mdsol/python313:latest AS python_base
#
# Stage 1.A) Get helper scripts (not currently used)
#
FROM python_base AS helper_scripts
RUN --mount=type=ssh git clone --depth=1 git@github.com:mdsol/engineering-helper-scripts.git ehs

#
# Stage 1.B) Install python packages
#
FROM python_base AS python_packages

ARG VENV_PATH
ARG PACKAGE_GROUPS
ARG POETRY_VERSION
WORKDIR $VENV_PATH

RUN pip install "poetry==$POETRY_VERSION"

COPY pyproject.toml poetry.lock $VENV_PATH

RUN --mount=type=secret,id=artifactory bash -c ' \
  source /run/secrets/artifactory && \
  python -m venv $VENV_PATH && \
  source $VENV_PATH/bin/activate && \
  POETRY_HTTP_BASIC_MDSOL_USERNAME="$ARTIFACTORY_USER" POETRY_HTTP_BASIC_MDSOL_PASSWORD="$ARTIFACTORY_TOKEN" \
  poetry install --no-interaction --no-ansi --no-root --with $PACKAGE_GROUPS'

# Add VENV_PATH to the PATH to be seamlessly used as the main python
#  (so that this stage can be used for testing without needing to build the UI)
# https://docs.docker.com/develop/develop-images/multistage-build/#stop-at-a-specific-build-stage
ENV PATH="${PATH}:${VENV_PATH}/bin"

#
# Stage 2) Install the app
#
FROM python_base as final

ARG APP_HOME
ARG VENV_PATH

# Copy python packages from package stage and setup env vars to point to them
# The method below only works if you have no compiled code
# Modify your Dockerfile to do a `poetry install` at the end of the build stage to
# correctly install compiled code
COPY --chown=app:app . $APP_HOME
COPY --chown=app:app --from=python_packages $VENV_PATH $VENV_PATH

# Setup paths so we have a functional python environment
ENV PATH="${VENV_PATH}/bin:${PATH}"
ENV PYTHONPATH="${APP_HOME}:${PYTHONPATH}"

WORKDIR $APP_HOME

# NOTE: Your application will need to modify this entrypoint
ENTRYPOINT [ "/bin/bash" ]
