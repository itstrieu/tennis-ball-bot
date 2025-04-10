import os
import glob


def get_misclassified_images(val_labels_dir, pred_labels_dir):
    """
    Identifies False Negatives (missed detections) and False Positives (wrong detections).
    """
    val_files = glob.glob(os.path.join(val_labels_dir, "*.txt"))
    pred_files = glob.glob(os.path.join(pred_labels_dir, "*.txt"))

    val_filenames = {os.path.basename(f).replace(".txt", "") for f in val_files}
    pred_filenames = {os.path.basename(f).replace(".txt", "") for f in pred_files}

    false_negatives = val_filenames - pred_filenames  # Missed detections
    false_positives = pred_filenames - val_filenames  # Incorrect detections

    return false_negatives, false_positives


def log_errors(false_negatives, false_positives, output_csv="error_analysis.csv"):
    """
    Saves misclassified images into a CSV file.
    """
    import pandas as pd

    error_data = {
        "False Negatives": list(false_negatives),
        "False Positives": list(false_positives),
    }

    df = pd.DataFrame(dict([(k, pd.Series(v)) for k, v in error_data.items()]))
    df.to_csv(output_csv, index=False)

    print(f"Error analysis saved to {output_csv}")
