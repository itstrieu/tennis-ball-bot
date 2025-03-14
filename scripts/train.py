import os
import time
import torch
import mlflow
import mlflow.pytorch
from ultralytics import YOLO
import yaml

# Constants
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
DATA_YAML_PATH = os.path.join(BASE_DIR, "data.yaml")
MAX_EPOCHS = 10  # Reduced for test training
BATCH_SIZE = 16
EXPERIMENT_NAME = "tennis-ball-bot-draft-train"

# ✅ Set MLflow Tracking URI
mlflow.set_tracking_uri("file:C:/Users/Dog/Documents/github/tennis-ball-bot/mlruns")

# Set MLflow experiment
mlflow.set_experiment(EXPERIMENT_NAME)

def train(config):
    """
    Runs the YOLO training loop with MLflow monitoring.
    """
    # ✅ Ensure MLflow logs under the correct experiment
    experiment = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
    if experiment is None:
        print(f"⚠️ Experiment '{EXPERIMENT_NAME}' does not exist! Creating...")
        experiment_id = mlflow.create_experiment(EXPERIMENT_NAME)
    else:
        experiment_id = experiment.experiment_id

    print(f"✅ MLflow Experiment ID: {experiment_id}")

    with mlflow.start_run(experiment_id=experiment_id):
        mlflow.log_param("epochs", config.epochs)
        mlflow.log_param("batch_size", config.batch_size)
        mlflow.log_param("device", config.device)

        # ✅ Train model while forcing logs into the correct experiment
        results = config.model.train(
            data=config.data_yaml,
            epochs=config.epochs,  # Best practice
            batch=config.batch_size,
            device=config.device,
        )

        metrics = results.results_dict
        print(f"📊 YOLO Training Metrics: {metrics}")

        mlflow.log_metric("training_loss", metrics.get("loss/box_loss", 0))
        mlflow.log_metric("mAP50", metrics.get("metrics/mAP50", 0))
        mlflow.log_metric("mAP50-95", metrics.get("metrics/mAP50-95", 0))

        # ✅ Log trained weights instead of the full model
        mlflow.log_artifact(config.model.ckpt_path, artifact_path="model")

        print(f"✅ Training completed: Loss={metrics.get('loss/box_loss', 0)}, mAP@50={metrics.get('metrics/mAP50', 0)}")

class TrainingConfig:
    """Holds YOLO training configuration settings."""

    def __init__(self, data_yaml, epochs, batch_size, device, model):
        self.data_yaml = data_yaml
        self.epochs = epochs
        self.batch_size = batch_size
        self.device = device
        self.model = model

if __name__ == "__main__":
    print("🔄 Preparing training configuration...")

    # Step 1: Load YOLO model
    yolo_model = YOLO("yolov8n.pt")
    DEVICE = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    yolo_model.to(DEVICE)

    # Step 2: Create training config and start training
    config = TrainingConfig(DATA_YAML_PATH, MAX_EPOCHS, BATCH_SIZE, DEVICE, yolo_model)
    train(config)

    print("✅ Training complete!")
