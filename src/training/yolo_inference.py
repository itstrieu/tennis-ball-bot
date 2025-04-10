from ultralytics import YOLO
import os


def run_yolo_inference(
    model_path,
    val_images_path,
    output_dir="runs/val_results",
    conf=0.25,
    iou=0.5,
    device="cuda",
):
    """
    Runs YOLO inference on the validation set and saves predictions.
    """
    model = YOLO(model_path)

    results = model.predict(
        source=val_images_path,
        save=True,
        save_txt=True,
        conf=conf,
        iou=iou,
        project="runs",
        name="val_results",
        device=device,
    )

    print(f"Inference completed. Results saved in {output_dir}/")
    return output_dir  # Path where results are saved
