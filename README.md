# **Tennis Ball Bot** 🤖  

## **Overview**  
Tennis Ball Bot is a vision-powered robotic system designed to detect and track tennis balls using **YOLOv8** and the **HAiLO AI Hat+** for real-time inference. The bot integrates object detection with sensor-based decision-making to autonomously locate tennis balls and navigate towards them.  

---

## **Features**  
✅ **Real-time Object Detection** – Fine-tuned **YOLOv8** model detects tennis balls efficiently.  
✅ **Edge AI Deployment** – Optimized inference on **HAiLO AI Hat+** with HEF format.  
✅ **Sensor Integration** – Uses **ultrasonic sensors** to confirm ball proximity.  
✅ **Autonomous Movement** – Moves towards detected tennis balls based on AI predictions.  

---

## **Project Structure**  
```
📦 tennis-ball-bot  
 ├── 📂 data              # Collected and annotated datasets  
 ├── 📂 models            # Trained YOLO models and HEF conversions  
 ├── 📂 scripts           # Scripts for training, evaluation, and sensor integration  
 ├── 📂 hardware          # Hardware setup instructions and motor control logic  \
 ├── 📜 project_notebook.ipynb 
 ├── 📜 README.md         # Project documentation  
 ├── 📜 requirements.txt  # Dependencies and environment setup  
 └── 📜 LICENSE           # Project licensing information  
```
---

## **Hardware Requirements**  
- **HAiLO AI Hat+** for edge computing  
- **Raspberry Pi / Arduino** for motor control  
- **Ultrasonic / LIDAR sensor** for distance measurement  
- **Differential drive system** for movement  

---

## **Evaluation Metrics**  
The model is optimized for:  
- **mAP@0.5** (primary metric)  
- **Latency (≥20 FPS)** for real-time execution  
- **Precision (≥90%) & Recall (≥85%)** to balance accuracy 
