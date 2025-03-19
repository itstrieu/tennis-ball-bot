from yolo_inference import run_yolo_inference
from analyze_errors import get_misclassified_images, log_errors
from visualize_errors import visualize_errors


# Paths
MODEL_PATH = r"C:\Users\Dog\Documents\github\tennis-ball-bot\mlruns\366693772092507800\226825cc9dd6404db44a1ba60da68329\artifacts\weights\best.pt"
VAL_IMAGES_PATH = r"C:\Users\Dog\Documents\github\tennis-ball-bot\data\images\val"
VAL_LABELS_DIR = r"C:\Users\Dog\Documents\github\tennis-ball-bot\data\labels\val"

# Run inference
# output_dir = run_yolo_inference(MODEL_PATH, VAL_IMAGES_PATH)

# Paths to results
# PRED_LABELS_DIR = f"{output_dir}/labels"
PRED_LABELS_DIR = (
    r"C:\Users\Dog\Documents\github\tennis-ball-bot\runs\val_results\labels"
)

# Find errors
false_negatives, false_positives = get_misclassified_images(
    VAL_LABELS_DIR, PRED_LABELS_DIR
)

# Log errors
log_errors(false_negatives, false_positives)

# Visualize misclassified images
visualize_errors(
    VAL_IMAGES_PATH,
    VAL_LABELS_DIR,
    PRED_LABELS_DIR,
    false_negatives,
    false_positives,
)
