#!/bin/bash


pytest \
    -m "not benchmark" \
    --cov python_template \
    --cov-report term \
    --cov-report html \
