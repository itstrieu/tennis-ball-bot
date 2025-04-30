import os
import torch
from ultralytics import YOLO
import argparse
import logging

# Create and configure logger
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def export_pt_to_onnx(
    pt_model_path: str, onnx_output_path: str, opset_version: int = 11
):
    """
    Loads a trained YOLO .pt model and exports it to ONNX format.

    Args:
        pt_model_path: Path to the input trained .pt model file.
        onnx_output_path: Desired path to save the output ONNX file.
        opset_version: The ONNX opset version to use for export.
    """
    if not os.path.exists(pt_model_path):
        logger.error(f"Input .pt model not found: {pt_model_path}")
        raise FileNotFoundError(f"Input .pt model not found: {pt_model_path}")

    logger.info(f"Loading model from: {pt_model_path}")
    try:
        # Load the trained YOLO model
        model = YOLO(pt_model_path)
        logger.info("Model loaded successfully.")

        # Extract the desired output filename
        output_filename = os.path.basename(onnx_output_path)
        # Extract the desired output directory
        output_directory = os.path.dirname(onnx_output_path)
        # If output_directory is empty, it means the user wants to save in the current dir
        if not output_directory:
            output_directory = "."

        # Ensure the output directory exists
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)
            logger.info(f"Created output directory: {output_directory}")

        # Extract the base filename without extension to use as the 'name' argument
        base_filename_without_ext = os.path.splitext(output_filename)[0]

        logger.info(
            f"Exporting model to ONNX format with opset version {opset_version}"
        )
        logger.info(
            f"Attempting to save ONNX to directory: {output_directory} with name: {base_filename_without_ext}"
        )

        # Export the model to ONNX
        # Use 'project' and 'name' to control output.
        # Based on the previous successful run, it saves directly to the 'project' directory
        # with filename derived from 'name'.
        model.export(
            format="onnx",
            opset=opset_version,
            project=output_directory,  # Use the output directory as the project
            name=base_filename_without_ext,  # Use the base filename as the name
        )

        # --- Corrected Logic for Finding the Saved File ---
        # Based on the previous successful ultralytics log, the file is saved directly in the project directory
        # with the filename derived from the 'name' argument and the .onnx extension.
        actual_saved_onnx_path = os.path.join(
            output_directory, f"{base_filename_without_ext}.onnx"
        )

        logger.info(
            f"Checking for exported file at the actual saved location: {actual_saved_onnx_path}"
        )

        if os.path.exists(actual_saved_onnx_path):
            logger.info(
                f"Model successfully exported to ONNX at: {actual_saved_onnx_path}"
            )
            # If the desired output path was different, inform the user where it was saved.
            # This check might be redundant now that the save location logic is aligned,
            # but keeping it for clarity.
            if (
                os.path.abspath(actual_saved_onnx_path).lower()
                != os.path.abspath(onnx_output_path).lower()
            ):
                logger.warning(
                    f"The exported file was saved to: {actual_saved_onnx_path}"
                )
                logger.warning(f"The requested output path was: {onnx_output_path}")

        else:
            # If not found, something unexpected happened.
            logger.error(
                "Could not find the exported ONNX file at the expected save location."
            )
            logger.error(
                "Export might have failed despite success message, or the save path logic is incorrect."
            )
            raise FileNotFoundError(
                "Exported ONNX file not found after running export."
            )

    except Exception as e:
        logger.error(f"Error during ONNX export: {e}")
        # Re-raise the exception to be caught by the main block
        raise


# ... (main block remains the same) ...
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Export YOLO .pt model to ONNX format."
    )
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        help="Path to the input trained .pt model file.",
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Desired path to save the output ONNX file.",
    )
    parser.add_argument(
        "--opset",
        type=int,
        default=11,
        help="The ONNX opset version to use for export.",
    )

    args = parser.parse_args()

    try:
        # Pass the desired output path. The function will use 'project' and 'name'
        # to control the output and check the actual save location.
        export_pt_to_onnx(args.model, args.output, args.opset)
    except Exception as e:
        logger.error(f"ONNX export script failed: {e}")
        exit(1)
