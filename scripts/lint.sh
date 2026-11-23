#!/bin/bash

set -e


pip install pre-commit
pre-commit install --install-hooks

# In CI we want to skip the git-config-checker since that is a local requirement for
# the individual developer's git client.
SKIP=git-config-checker pre-commit run --all-files
