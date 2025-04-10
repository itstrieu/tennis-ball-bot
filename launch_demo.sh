#!/bin/bash
cd "$(dirname "$0")"
source pi-yolo/bin/activate
PYTHONPATH=src python3 demo_robot.py

