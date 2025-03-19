import os

# Define dataset path (modify as needed)
DATASET_DIR = "data"
TEST_IMAGES_DIR = os.path.join(DATASET_DIR, "images", "test")
OUTPUT_FILE = os.path.join(DATASET_DIR, "test.txt")

# Get all image filenames in the test images directory
image_extensions = (".jpg", ".jpeg", ".png", ".bmp", ".PNG")
test_images = [f for f in os.listdir(TEST_IMAGES_DIR) if f.endswith(image_extensions)]

# Convert filenames to full relative paths
test_image_paths = [os.path.join("images", "test", img) for img in test_images]

# Write to test.txt
with open(OUTPUT_FILE, "w") as f:
    for path in test_image_paths:
        f.write(path + "\n")

print(f"test.txt generated successfully with {len(test_image_paths)} entries.")
