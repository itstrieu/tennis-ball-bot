import os
import torch
import mlflow
import mlflow.pytorch
from ultralytics import YOLO
from training.config import TrainingConfig
import logging

# Create and configure logger
logging.basicConfig(
    filename=os.path.join(os.getcwd(), "yolo_experiment.log"),
    format="%(name)s %(asctime)s %(levelname)s - %(message)s",
    filemode="a",
    force=True,
    level=logging.INFO,
)

# Create a logger
logger = logging.getLogger(__name__)


def setup_mlflow(config):
    """Ensures the MLflow experiment exists and starts a new run."""
    if not config.tracking_uri:
        raise ValueError("MLflow Tracking URI is not set in the configuration.")

    # Set MLflow tracking URI
    mlflow.set_tracking_uri(config.tracking_uri)

    try:
        experiment = mlflow.get_experiment_by_name(config.experiment_name)
        if experiment is None:
            logger.info(f"Creating a new MLflow experiment: {config.experiment_name}")
            experiment_id = mlflow.create_experiment(config.experiment_name)
        else:
            experiment_id = experiment.experiment_id

        logger.info(f"Using MLflow Experiment ID: {experiment_id}")
        return experiment_id
    except Exception as e:
        logger.error(f"MLflow setup failed.: {e}")
        raise RuntimeError(f"MLflow experiment setup failed: {e}") from e


def train(config, experiment_id, device, data_yaml):
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
                    "device": str(device),
                    "cache": config.cache,
                    "profile": config.profile,
                }
            )

            # Start YOLO training with parameters from the config
            results = config.model.train(
                data=data_yaml,
                epochs=config.epochs,
                batch=config.batch_size,
                device=device,
                cache=config.cache,
                profile=config.profile,
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

    except Exception as e:
        logger.error(f"Training failed: {e}")
        if run_started:
            mlflow.end_run(status="FAILED")
        raise
    finally:
        if run_started:
            mlflow.end_run()


def save_model():

    # Log the actual model file in MLflow
    mlflow.log_artifact(config.model_path, artifact_path="trained_models")

    print(f"Fine-tuned model saved and logged from: {config.model_path}")


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
    config.model = yolo_model

    # Assign path to data.yaml
    data_yaml = os.getenv("DATA_YAML_PATH")

    # Set up MLflow experiment
    experiment_id = setup_mlflow(config)

    # Start training
    train(config, experiment_id, DEVICE, data_yaml)

    # Save model after training
    save_model()

    logger.info("Training complete!")

    # Ensure logs are properly written before script exits
    logging.shutdown()
