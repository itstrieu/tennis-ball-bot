# Tennis Ball Bot

A Raspberry Pi robot that finds tennis balls, drives to them and picks them up. Built February to May 2025 with a team of mechanical engineering students. I wrote the software: vision, data, training, and movement control.

The original plan is in the [Project Notebook](project_notebook.md), and progress against it is in the [To-Do List](todo_list.md).

<video src="https://github.com/user-attachments/assets/51e9fd58-1a18-44bb-ae33-781211b183f4"></video>

## What it does

1. The camera captures a frame.
2. A fine-tuned YOLO model finds the tennis ball and returns its bounding box.
3. The strategy module decides how to move, based on how far the ball is from center (corrected for camera offset) and how large its box is.
4. The ultrasonic sensor overrides movement if something is too close.
5. The motion controller sends the movement commands to the motors.

A live view of the detection feed streams through FastAPI and a Cloudflare tunnel.

## Data and training

- Recorded my own video of tennis balls across varied environments and labeled it in CVAT with 2D bounding boxes.
- Planned the split so that the test set holds real-world footage only.
- Fine-tuned YOLO over multiple epochs, with MLflow tracking the test run.
- Ran error analysis on false positives and false negatives (`src/training/analyze_errors.py`, `visualize_errors.py`).
- Evaluated the final model on a held-out test set of real-world footage the model never saw in training: precision and recall above 90%.

**Targets set before training:** mAP@0.5 as the metric to optimize. Latency of at least 20 FPS, precision of at least 90% and recall of at least 85% as thresholds to meet.

## Hardware

- Raspberry Pi 5 with a camera module
- Motors driven over GPIO, first omni-wheel, later differential drive
- Ultrasonic sensor for collision avoidance

Much of the final month was tuning movement on the physical robot: rotation speed and duration, forward calibration, and re-tuning after a motor swap.

## Code layout

```
src/
  app/          robot_controller.py (the main loop), camera_manager.py
  config/       motion, pin and vision settings
  core/
    detection/  YOLO inference and ball tracking
    navigation/ motor control
    sensors/    ultrasonic sensor
    strategy/   movement decisions
  streaming/    FastAPI stream server, performance monitor
  training/     training, error analysis, ONNX export script
  utils/        logging
```

Each module takes its configuration through its constructor, so any part can be tested on its own.

## Planned, not built

These were in the original plan and never finished:

- Converting the model to HEF and running inference on the Hailo AI Hat+ (inference runs on the Pi with Ultralytics)
- Quantization for edge deployment
- Prometheus and Grafana monitoring on the Pi
- Automated retraining through CI/CD
- LIDAR
