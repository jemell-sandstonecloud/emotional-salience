#!/bin/bash
cd "$(dirname "$0")"
python -m pytest tests/ -v --tb=short 2>&1
