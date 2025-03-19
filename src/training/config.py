import os
import yaml
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()


class TrainingConfig:
    """Loads YOLO training settings from config.yaml and .env dynamically."""

    def __init__(self):
        """Initialize training configuration with YAML and environment variables."""

        # Load CONFIG_PATH from .env or fallback to default
        config_path = os.getenv("CONFIG_PATH", "config.yaml")

        # Ensure absolute path
        self.config_path = os.path.abspath(config_path)

        # Load configuration file
        self.config = self.load_config(self.config_path)

        # Model Paths
        model_dir = os.getenv("MODEL_PATH", "")  # Directory from .env
        model_file = self.config["model"]["file"]  # Filename from config.yaml
        self.model_path = os.path.join(model_dir, model_file)  # Full path to model

        # Training Parameters (Use config.yaml)
        self.model = None
        self.data_yaml = os.path.abspath(self.config["training"]["data_yaml"])
        self.epochs = self.config["training"]["max_epochs"]
        self.batch_size = self.config["training"]["batch_size"]
        self.cache = self.config["training"]["cache"]
        self.profile = self.config["training"]["profile"]

        # MLflow Tracking URI (Ensure correct format for Windows)
        tracking_path = os.getenv("MLFLOW_TRACKING_URI", self.config_path)
        self.tracking_uri = (
            f"file:{os.path.abspath(tracking_path)}"
            if ":" in tracking_path
            else tracking_path
        )

        # Experiment Name from .env
        self.experiment_name = os.getenv("EXPERIMENT_NAME", "default-experiment")

    @staticmethod
    def load_config(config_path):
        """Loads YAML config file."""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, "r") as file:
            return yaml.safe_load(file)


# Example Usage
if __name__ == "__main__":
    config = TrainingConfig()
    print(f"Config Path: {config.config_path}")
    print(f"Model Path: {config.model_path}")
    print(f"Training for {config.epochs} epochs with batch size {config.batch_size}.")
    print(f"Experiment Name: {config.experiment_name}")
    print(f"Tracking URI: {config.tracking_uri}")
