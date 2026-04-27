#!/bin/bash


pytest \
    -m "not benchmark" \
    --cov dataconnect_library_python \
    --cov-report term \
    --cov-report html \
