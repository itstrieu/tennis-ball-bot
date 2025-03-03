# **Tennis Ball Bot** 🤖  
Work-in-Progress. See the [project notebook](https://github.com/itstrieu/tennis-ball-bot/blob/main/project_notebook.ipynb) for project plans and progress.  

## **Overview**  
Tennis Ball Bot is a vision-powered robotic system designed to detect and track tennis balls using **YOLOv8** and the **HAiLO AI Hat+** for real-time inference. The bot integrates object detection with sensor-based decision-making to autonomously locate and navigate towards tennis balls.  

## **Features**  
- **Real-time Object Detection** – Fine-tuned **YOLOv8n** (nano version) model optimized for edge devices.  
- **Edge AI Deployment** – Runs on **HAiLO AI Hat+** using **HEF format** for low-power, real-time inference.  
- **Sensor Integration** – Uses **ultrasonic sensors** to confirm ball proximity and avoid obstacles.  
- **Autonomous Navigation** – Moves toward detected tennis balls using AI-driven decision-making.  

## **Project Structure**  
```
📦 tennis-ball-bot  
 ├── 📂 data              # Collected and annotated datasets  
 ├── 📂 models            # Trained YOLO models and HEF conversions  
 ├── 📂 scripts           # Scripts for training, evaluation, and sensor integration  
 ├── 📂 hardware          # Hardware setup instructions and motor control logic  
 ├── 📜 project_notebook.ipynb  
 ├── 📜 README.md         # Project documentation  
 ├── 📜 requirements.txt  # Dependencies and environment setup  
 └── 📜 LICENSE           # Project licensing information  
```

## **Data Collection & Model Training**  
- **Custom Dataset Annotation** – Video footage collected in diverse environments (indoor/outdoor, different lighting conditions).  
- **Annotation Tool** – **CVAT** for 2D bounding box labeling.  
- **Train/Dev/Test Split**:  
  - **Training Set**: Majority of collected data for fine-tuning.  
  - **Training-Dev Set**: Subset of training data reserved for validation.  
  - **Test Set**: Real-world data only, ensuring reliable evaluation.  

## **Hardware Requirements**  
- **HAiLO AI Hat+** for edge computing  
- **Raspberry Pi 5** for control and processing  
- **Ultrasonic / LIDAR sensors** for obstacle detection  
- **Differential drive system** for movement  

## **Evaluation Metrics**  
The model is optimized for:  
- **mAP@0.5** (Mean Average Precision) – Ensures accurate object detection.  
- **Latency (≥20 FPS / ≤50ms per frame)** – Enables real-time execution.  
- **Precision (≥90%) & Recall (≥85%)** – Balances accuracy and efficiency.  

## **Real-Time Inference Monitoring**  
To monitor performance on the **Raspberry Pi 5 + HAiLO AI Hat+**, the project integrates **Prometheus** and **Grafana**:  
- **Prometheus** – Collects real-time inference metrics (FPS, latency, accuracy).  
- **Grafana** – Visualizes metrics with real-time dashboards.  
