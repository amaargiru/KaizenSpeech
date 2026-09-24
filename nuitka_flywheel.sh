#!/usr/bin/env bash

python -m nuitka --follow-imports --standalone --output-dir="nuitka_out" "./Code/flywheel.py"
