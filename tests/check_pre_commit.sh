#!/usr/bin/env bash

set -e

pip install -e .
pip install pre-commit
pre-commit run --all-files

# check that no files have changed.
git diff-tree --no-commit-id --name-only -r $REVISION | xargs pre-commit run --files
