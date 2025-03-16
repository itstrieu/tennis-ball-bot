# **Tennis Ball Bot**

### **Goal:**

Build a robot that can identify and pick up tennis balls autonomously.

### **Required Skills and Knowledge**

#### **Machine Learning & Computer Vision**

Object detection, YOLO (YOLOv4-tiny, YOLOv5, YOLOv8), model training, MLflow, hyperparameter tuning, experiment tracking, OpenCV, image processing, data augmentation, PyTorch, TensorFlow.

#### **Software Development & Deployment**

Python, NumPy, Pandas, Matplotlib, Scipy, Git, GitHub, CI/CD, GitHub Actions, SSH, SCP, Raspberry Pi deployment.

#### **Embedded Systems & Hardware**

Raspberry Pi 5, HAiLO AI Hat+, RPi.GPIO, TB6612 motor drivers, camera module integration, motor control, PWM speed adjustments.

#### **DevOps & Monitoring**

Prometheus, Grafana, real-time performance monitoring, logging, debugging, embedded AI applications.

#### **Web Hosting & APIs**

FastAPI, WebRTC, MJPEG streaming, API server deployment, remote access, live video hosting.

---

## **1. Machine Learning Production Pipeline**

### **Scoping**

The core machine learning task is object detection, specifically identifying tennis balls in diverse environments. The model must be:

- **Efficient:** Low power consumption for real-time inference.
- **Accurate:** High detection precision and recall.
- **Deployable:** Compatible with the HAiLO AI Hat+ on a Raspberry Pi 5.

---

### **Live Video Streaming with FastAPI**

To enable remote monitoring of the Tennis Ball Bot’s object detection system, a **FastAPI** server will be set up to host a live video feed.

#### **FastAPI Server Implementation**

The FastAPI server will stream real-time footage from the Raspberry Pi’s camera module. The video feed will include bounding boxes drawn around detected tennis balls using the YOLOv8 object detection model.

The FastAPI application will expose an endpoint where users can access the live video stream remotely. The camera feed will be processed frame-by-frame, and detection results will be overlaid onto the video output before being streamed.

To ensure smooth performance:
- OpenCV will be used for handling video capture and processing.
- The YOLO model will process each frame in real time.
- The server will return a continuous stream of frames containing bounding boxes for detected tennis balls.

#### **Deployment and Access**

The FastAPI server will be deployed on the Raspberry Pi and run continuously while the bot is operating. Users will be able to access the video stream by visiting a specified URL in a web browser.

The live feed will be accessible over the local network, but it can be configured for remote access using port forwarding or a cloud-based relay service if needed.

This setup will allow for real-time monitoring of the robot’s environment, enabling debugging and performance evaluation while the bot is running.

---

### **Model Deployment & Monitoring**

To streamline deployment and ensure stability, **Continuous Integration/Continuous Deployment (CI/CD)** will be implemented using **GitHub Actions**, and **Prometheus** and **Grafana** will be used for monitoring.

---

## **2. Sensor Integration**

- **Sensor Inputs:** TBD

---

## **3. Movement**

The Tennis Ball Bot's movement is powered by **omni wheels**, allowing smooth multidirectional navigation. Two motor systems drive functionality:

- **Wheel Motors:** Control movement and navigation.
- **Rotating Cylinder Motor:** Operates the ball pickup mechanism.

For motor control, the **RPi.GPIO** library will be used to allow precise direction settings and **PWM-based speed adjustments**. This ensures smooth acceleration, deceleration, and accurate movement for both navigation and ball collection. The **TB6612 motor drivers** will interface with the Raspberry Pi 5 to provide stable and efficient control over the motors.

---

## **4. Hardware Components**

The Tennis Ball Bot is built using the following key hardware components:

- **Raspberry Pi 5:** The central processing unit that handles computation and model inference.
- **HAiLO AI Hat+:** The AI accelerator that enables efficient object detection.
- **Camera Module:** Captures real-time footage for object detection.
- **Wheels:** Omni wheels enable multidirectional movement.
- **Motors:** Drive the wheels and ball pickup system.
- **Motor Drivers:** The **TB6612 motor drivers** ensure reliable motor operation.
