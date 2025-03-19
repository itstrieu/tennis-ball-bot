import os
import torch
import mlflow
import mlflow.pytorch
from ultralytics import YOLO
from utils.logger import logger
from training.config import TrainingConfig


def setup_mlflow(config):
    """Ensures the MLflow experiment exists and starts a new run."""
    if not config.tracking_uri:
        raise ValueError("MLflow Tracking URI is not set in the configuration.")

    # Set MLflow tracking URI
    mlflow.set_tracking_uri(config.tracking_uri)

    try:
        experiment = mlflow.get_experiment_by_name(
            "sanity-check-after-refactoring"
        )  # Experiment name is static now
        if experiment is None:
            logger.info(
                "Creating a new MLflow experiment: sanity-check-after-refactoring"
            )
            experiment_id = mlflow.create_experiment("sanity-check-after-refactoring")
        else:
            experiment_id = experiment.experiment_id

        logger.info(f"Using MLflow Experiment ID: {experiment_id}")
        return experiment_id
    except Exception as e:
        logger.error(f"MLflow setup failed.: {e}")
        raise RuntimeError(f"MLflow experiment setup failed: {e}") from e


def train(config, experiment_id):
    """
    Runs the YOLO training loop with MLflow monitoring.
    """
    logger.info("Starting training...")
    run_started = False

    try:
        # Begin an MLflow experiment run
        with mlflow.start_run(experiment_id=experiment_id):
            run_started = True

            # Log training hyperparameters
            mlflow.log_params(
                {
                    "epochs": config.epochs,
                    "batch_size": config.batch_size,
                    "device": DEVICE,
                }
            )

            # Start YOLO training with parameters from the config
            results = config.model.train(
                data=data_yaml,
                epochs=config.epochs,
                batch=config.batch_size,
                device=DEVICE,
            )

            # Extract training metrics
            metrics = results.results_dict

            # Log the metrics
            logger.info(f"Training Metrics: {metrics}")

            # Log the metrics in MLflow
            mlflow.log_metrics(
                {
                    "training_loss": metrics.get("loss/box_loss", 0),
                    "mAP50": metrics.get("metrics/mAP50", 0),
                    "mAP50-95": metrics.get("metrics/mAP50-95", 0),
                }
            )

            # Save the trained model weights in MLflow under "model" directory
            mlflow.log_artifact(config.model_path, artifact_path="model")

    except Exception as e:
        logger.error(f"Training failed: {e}")
        if run_started:
            mlflow.end_run(status="FAILED")
        raise
    finally:
        if run_started:
            mlflow.end_run()


if __name__ == "__main__":
    logger.info("Preparing training configuration...")

    # Load configuration
    config = TrainingConfig()

    # Ensure model file exists
    if not os.path.exists(config.model_path):
        raise FileNotFoundError(f"Model file not found: {config.model_path}")

    # Load YOLO model
    yolo_model = YOLO(config.model_path)
    DEVICE = torch.device(
        "cuda:0"
        if torch.cuda.is_available() and torch.cuda.device_count() > 0
        else "cpu"
    )
    yolo_model.to(DEVICE)
    config.model = yolo_model  # ✅ Assign model to config

    # Assign path to data.yaml
    data_yaml = os.getenv("DATA_YAML_PATH")

    # Set up MLflow experiment
    experiment_id = setup_mlflow(config)

    # Start training
    train(config, experiment_id)

    logger.info("Training complete!")
