"""
train.py - Fine-tunes YOLOv8n and monitors training with Prometheus.
"""

import time
import torch
from ultralytics import YOLO
from prometheus_client import start_http_server, Gauge

# Constants
PROMETHEUS_PORT = 8001
DATA_YAML_PATH = "data.yaml"
MAX_EPOCHS = 50
BATCH_SIZE = 16

# Prometheus Metrics
LOSS_GAUGE = Gauge("training_loss", "Current training loss")
MAP50_GAUGE = Gauge("map50", "Mean Average Precision @ 50 IoU")
BATCH_TIME_GAUGE = Gauge("batch_time", "Time taken per batch")
GPU_USAGE_GAUGE = Gauge("gpu_memory_usage_mb", "GPU memory usage in MB")
GPU_UTILIZATION_GAUGE = Gauge("gpu_utilization", "GPU utilization percentage")


class TrainingConfig:
    """Holds YOLO training configuration settings."""

    def __init__(self, data_yaml, epochs, batch_size, device, model):
        self.data_yaml = data_yaml
        self.epochs = epochs
        self.batch_size = batch_size
        self.device = device
        self.model = model


def monitor_gpu():
    """
    Monitors and updates GPU memory and utilization metrics.
    """
    if torch.cuda.is_available():
        gpu_memory = torch.cuda.memory_allocated(0) / (1024 * 1024)  # Convert to MB
        gpu_utilization = torch.cuda.utilization(0)  # GPU Utilization %

        GPU_USAGE_GAUGE.set(gpu_memory)
        GPU_UTILIZATION_GAUGE.set(gpu_utilization)


def train(config):
    """
    Runs the YOLO training loop with Prometheus monitoring.
    """
    for epoch in range(config.epochs):
        start_time = time.time()

        results = config.model.train(
            data=config.data_yaml,
            epochs=1,  # Train one epoch at a time to monitor results
            batch=config.batch_size,
            device=config.device,
        )

        # Extract metrics
        loss = results.results[0]  # Loss
        map50 = results.results[1]  # mAP@50

        # Update Prometheus metrics
        LOSS_GAUGE.set(loss)
        MAP50_GAUGE.set(map50)
        BATCH_TIME_GAUGE.set(time.time() - start_time)

        monitor_gpu()

        print(f"Epoch {epoch+1}: Loss={loss}, mAP@50={map50}")


if __name__ == "__main__":
    start_http_server(PROMETHEUS_PORT)  # Start Prometheus server

    # Load YOLO model
    yolo_model = YOLO("yolov8n.pt")  # Load pre-trained YOLOv8 nano
    DEVICE = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    yolo_model.to(DEVICE)

    # Create training config and start training
    config = TrainingConfig(DATA_YAML_PATH, MAX_EPOCHS, BATCH_SIZE, DEVICE, yolo_model)
    train(config)
