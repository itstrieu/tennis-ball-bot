# **Tennis Ball Bot**

### **Goal:**

Build a robot that can identify and pick up tennis balls autonomously.

### **Required Skills and Knowledge**

#### **Machine Learning & Computer Vision**

Object detection, YOLO (YOLOv8), model training, MLflow, hyperparameter tuning, experiment tracking, OpenCV, image processing, data augmentation, model quantization, ONNX conversion, edge AI optimization.

#### **Software Development & Deployment**

Python, Pandas, Git, GitHub, CI/CD, GitHub Actions, SSH, Raspberry Pi deployment, model versioning, automated model retraining.

#### **Embedded Systems & Hardware**

Raspberry Pi 5, HAiLO AI Hat+, RPi.GPIO, TB6612 motor drivers, camera module integration, motor control, PWM speed adjustments, sensor synchronization, omni-wheel drive system.

#### **DevOps & Monitoring**

Prometheus, Grafana, real-time performance monitoring, logging, debugging, embedded AI applications, model performance benchmarking.

#### **Web Hosting & APIs**

FastAPI, WebRTC, MJPEG streaming, API server deployment, remote access, Cloudflare Tunnel, live video hosting.

---

## **1. Machine Learning Production Pipeline**

### **Scoping**

The core machine learning task is object detection, specifically identifying tennis balls in diverse environments. The model must be:

- **Efficient:** Low power consumption for real-time inference.
- **Accurate:** High detection precision and recall.
- **Deployable:** Compatible with the HAiLO AI Hat+ on a Raspberry Pi 5.

---

## **2. Data Engineering**

To ensure robust and real-world performance, I will collect and annotate my own dataset. While pre-annotated datasets exist online, they may not fully represent the conditions my robot will encounter. To address this, I will:

- Capture video footage of tennis balls in diverse environments (e.g., indoor/outdoor, day/night, different backgrounds).  
- Use **CVAT** for annotation, applying **2D bounding boxes** to label tennis balls across frames.  

**Dataset Composition:**  
If necessary, I will incorporate additional online datasets to increase training diversity. However, to prevent distribution mismatch, the development and test sets will only contain real-world data.

**Train/Dev/Test Split:**  
- **Training Set:** Includes the majority of the collected data for fine-tuning.  
- **Training-Dev Set:** A subset of the training data, reserved for model validation but not used during training.  
- **Test Set:** Exclusively real-world data, ensuring an accurate evaluation of model performance.  

---

## **3. Model Training**

Since I will be deploying my object detection model on the **HAiLO AI Hat+**, I need to ensure compatibility with the device's constraints. The HAiLO accelerator requires models to be in **HEF (HAiLO Executable Format)**, which impacts my choices for model selection, optimization, and deployment.

**Model Compatibility:**  
The HAiLO Model Compiler supports specific architectures, so I will need to work within the following constraints:

- The model must be compatible with **HAiLO’s runtime**, which supports **YOLO-based models (YOLOv4-tiny, YOLOv5, YOLOv8) and MobileNet-based models**.  
- The model should be optimized for **low power consumption and real-time inference**.  
- Given these factors, I plan to **fine-tune YOLOv8n (nano version)**, as it provides a good balance between **accuracy and efficiency** for edge devices.  

**YOLO Optimization for HAiLO AI Hat+ (HEF Format):**  
- Convert trained YOLO model to **ONNX format**  
- Optimize ONNX model using **HAiLO Model Zoo tools**  
- Apply **quantization** to reduce model size while maintaining accuracy  
- Convert optimized model to **HEF (HAiLO Executable Format)**  
- Test HEF model inference on HAiLO AI Hat+  
- Benchmark performance (FPS, latency, accuracy) before and after optimization  
- Ensure model is **compatible with edge deployment constraints**  

**Model Evaluation:**  
Since I am not tracking and focusing on object detection, my key concern is detecting tennis balls accurately and efficiently in a real-time system.

**Optimizing Metric (Primary focus):**  
- **mAP@0.5 (Mean Average Precision at IoU 0.5)** – Ensures bounding boxes overlap significantly with ground truth.  

**Satisficing Metrics (Must meet thresholds):**  
- **Latency (Inference Speed) ≥ 20 FPS (≤ 50ms per frame)** – Ensures the model runs in real-time.  
- **Precision @ IoU 0.5 Threshold: ≥ 90%** – Avoid false positives.  
- **Recall @ IoU 0.5 ≥ 85%** – Ensure all tennis balls are detected.  

---

## **4. Model Deployment**

### **Live Video Streaming with FastAPI**

To enable remote monitoring of the Tennis Ball Bot’s object detection system, a **FastAPI** server will be set up to host a live video feed.

**Deployment and Access:**  
- The FastAPI server will be deployed on the Raspberry Pi and run continuously while the bot is operating.  
- The live feed will be accessible over the local network but can be configured for remote access using **Cloudflare Tunnel**, ensuring **secure public access** without exposing the Raspberry Pi to direct internet traffic.  

---

## **5. Model Monitoring**

To streamline deployment and ensure stability, **Continuous Integration/Continuous Deployment (CI/CD)** will be implemented using **GitHub Actions**, and **Prometheus** and **Grafana** will be used for monitoring.

To monitor performance on the **Raspberry Pi 5 + HAiLO AI Hat+**, the project integrates **Prometheus** and **Grafana**:

- **Prometheus** – Collects real-time inference metrics (FPS, latency, accuracy, sensor feedback).  
- **Grafana** – Visualizes system telemetry and model performance with real-time dashboards.  

### **Live Dashboard Example**
- YOLO Inference Speed (FPS)  
- Latency per Frame  
- Detected Objects & Confidence Scores  
- Motor Speed & Sensor Readings  
- System Temperature & Power Usage  

---

## **6. Sensor Integration**

- Program and test **ultrasonic sensors** for obstacle detection  
- Sync sensor input with **YOLO object detection**  
- Implement **failsafe mechanisms** (e.g., stop if detection fails or an obstacle appears)  
- Optimize sensor response time for real-time navigation  

---

## **7. Movement**

The Tennis Ball Bot's movement is powered by **omni wheels**, allowing smooth multidirectional navigation.

- **Wheel Motors:** Control movement and navigation.  
- **Rotating Cylinder Motor:** Operates the ball pickup mechanism.  

### **Movement Synchronization**
- Program robot movement to **approach and retrieve tennis balls**  
- Sync movement control with **YOLO object detection outputs**  
- Integrate **sensor feedback** to optimize movement decisions  
- Implement **collision avoidance** using sensor data and AI-based adjustments  
