#!/usr/bin/env bash

set -e

pip install -e .
pip install pre-commit
pre-commit run --all-files
