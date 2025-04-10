import cv2
import os
import matplotlib.pyplot as plt


class ErrorVisualizer:
    def __init__(
        self,
        image_dir,
        val_labels_dir,
        pred_labels_dir,
        false_negatives,
        false_positives,
    ):
        """
        Initializes the interactive error visualizer.
        """
        self.image_dir = image_dir
        self.val_labels_dir = val_labels_dir
        self.pred_labels_dir = pred_labels_dir
        self.error_samples = list(false_negatives) + list(false_positives)
        self.index = 0  # Start with the first image

        if not self.error_samples:
            print("No errors found.")
            return

        self.fig, self.axs = plt.subplots(1, 2, figsize=(12, 6))
        self.fig.canvas.mpl_connect("key_press_event", self.on_key)
        self.show_image()
        plt.show()

    def draw_boxes(self, image_path, label_path, color=(0, 255, 0), label="GT"):
        """
        Draws bounding boxes from a YOLO label file onto an image.
        """
        img = cv2.imread(image_path)
        if not os.path.exists(label_path):
            return img  # Return image as is if label file is missing

        with open(label_path, "r") as f:
            lines = f.readlines()

        for line in lines:
            parts = line.strip().split()
            x, y, w, h = map(float, parts[1:5])
            x, y, w, h = (
                int(x * img.shape[1]),
                int(y * img.shape[0]),
                int(w * img.shape[1]),
                int(h * img.shape[0]),
            )
            cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
            cv2.putText(img, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        return img

    def show_image(self):
        """
        Displays the current image with ground truth and predicted bounding boxes.
        """
        if not self.error_samples:
            return

        img_name = self.error_samples[self.index]
        img_path = os.path.join(self.image_dir, f"{img_name}.PNG")
        gt_label_path = os.path.join(self.val_labels_dir, f"{img_name}.txt")
        pred_label_path = os.path.join(self.pred_labels_dir, f"{img_name}.txt")

        img_gt = self.draw_boxes(
            img_path, gt_label_path, color=(0, 255, 0), label="Ground Truth"
        )
        img_pred = self.draw_boxes(
            img_path, pred_label_path, color=(0, 0, 255), label="Prediction"
        )

        self.axs[0].cla()
        self.axs[1].cla()

        self.axs[0].imshow(cv2.cvtColor(img_gt, cv2.COLOR_BGR2RGB))
        self.axs[0].set_title(f"Ground Truth - {img_name}")
        self.axs[0].axis("off")

        self.axs[1].imshow(cv2.cvtColor(img_pred, cv2.COLOR_BGR2RGB))
        self.axs[1].set_title(f"Prediction - {img_name}")
        self.axs[1].axis("off")

        plt.draw()

    def on_key(self, event):
        """
        Handles keyboard events for navigation.
        Left arrow = Previous image, Right arrow = Next image.
        """
        if event.key == "right":  # Next image
            self.index = (self.index + 1) % len(self.error_samples)
        elif event.key == "left":  # Previous image
            self.index = (self.index - 1) % len(self.error_samples)
        self.show_image()


def visualize_errors(
    image_dir, val_labels_dir, pred_labels_dir, false_negatives, false_positives
):
    """
    Launches the interactive visualization for error analysis.
    """
    ErrorVisualizer(
        image_dir, val_labels_dir, pred_labels_dir, false_negatives, false_positives
    )
