# **Tennis Ball Bot**  

Work-in-Progress. See the [Project Notebook](https://github.com/itstrieu/tennis-ball-bot/blob/main/project_notebook.md) for project plans and [To-Do List](https://github.com/itstrieu/tennis-ball-bot/blob/main/todo_list.md) for project progress.  

<video src="https://github.com/user-attachments/assets/51e9fd58-1a18-44bb-ae33-781211b183f4"></video>

## **Overview**  

Tennis Ball Bot is a vision-powered robotic system designed to autonomously detect, track, and retrieve tennis balls using **YOLOv8** and the **HAiLO AI Hat+** for real-time inference. The bot integrates computer vision, sensor-based navigation, and AI-powered movement, making it a fully independent system capable of interacting with real-world environments.

## **Key Features**

- **Real-time Object Detection** – Fine-tuned **YOLOv8n** model optimized for edge computing.  
- **Edge AI Deployment** – Runs on **HAiLO AI Hat+** using **HEF format** for low-power, real-time inference.  
- **Autonomous Ball Retrieval** – AI-driven navigation to track and retrieve tennis balls.  
- **Hardware & Sensor Integration** – Uses **ultrasonic sensors** for collision avoidance and **motorized movement**.  
- **Remote Monitoring & Visualization** – FastAPI + Cloudflare Tunnel for live streaming and system telemetry.  
- **Real-Time Performance Monitoring** – **Prometheus & Grafana** track inference latency, FPS, and system performance.  
- **Automated Model Retraining** – **MLflow-powered CI/CD pipeline** to continuously improve detection performance.  

## **Directory Structure**

```markdown
/tennis-ball-bot
│
├── src/                             # Main source code for the project
│   ├── app/                         # Application-level components
│   │   ├── __init__.py              # Marks this folder as a package
│   │   ├── robot_controller.py      # Controls the main robot behavior
│   │   └── __init__.py              # Marks this folder as a package
│   │
│   ├── config/                      # Configuration files for pins, motion, and constants
│   │   ├── __init__.py              # Marks this folder as a package
│   │   ├── constants.py             # Project-wide constants
│   │   ├── motion.py                # Motion configuration
│   │   ├── pins.py                  # Pin mappings for the hardware
│   │   ├── system.py                # System-specific configurations
│   │   └── vision.py                # Vision configuration (e.g., YOLO model)
│   │
│   ├── core/                        # Core functionality of the robot
│   │   ├── __init__.py              # Marks this folder as a package
│   │   ├── navigation/              # Navigation and motion control logic
│   │   │   ├── __init__.py          # Marks this folder as a package
│   │   │   ├── encoders.py          # Encoder-related logic
│   │   │   └── motion_controller.py # Controls motor movement and direction
│   │   │
│   │   ├── detection/               # Object detection (YOLO) logic
│   │   │   ├── __init__.py          # Marks this folder as a package
│   │   │   ├── vision_tracker.py    # Tracks and handles object detection
│   │   │   └── yolo_inference.py    # YOLO inference for real-time object detection
│   │   │
│   │   ├── sensors/                 # Sensor control and integration
│   │   │   ├── __init__.py          # Marks this folder as a package
│   │   │   └── ultrasonic_sensor.py # Ultrasonic sensor for distance measurement
│   │   │
│   │   ├── strategy/                # AI decision-making logic
│   │   │   ├── __init__.py          # Marks this folder as a package
│   │   │   ├── movement_decider.py  # Decides robot movement strategy
│   │   │   └── __init__.py          # Marks this folder as a package
│   │   │
│   │   └── streaming/               # Streaming and remote access components
│   │       ├── __init__.py          # Marks this folder as a package
│   │       ├── camera_streamer.py   # Manages camera feed streaming
│   │       ├── performance_monitor.py # Monitors system performance in real-time
│   │       └── stream_client.py     # Handles communication with streaming services
│   │
│   ├── training/                    # Model training and evaluation components
│   │   ├── __init__.py              # Marks this folder as a package
│   │   ├── analyze_errors.py        # Analyzes model prediction errors
│   │   ├── config.py                # Configuration for training parameters
│   │   ├── error_analysis_main.py   # Main logic for error analysis
│   │   ├── train.py                 # Model training logic
│   │   ├── visualize_errors.py      # Visualizes model error data
│   │   ├── yolo_inference.py       # YOLO model inference logic
│   │   └── yolo11n.pt              # YOLO model weights
│   │
│   └── utils/                       # Utility functions and helpers
│       ├── __init__.py              # Marks this folder as a package
│       ├── logger.py                # Logger utility for centralized logging
│       └── __init__.py              # Marks this folder as a package
│
├── .env                             # Environment variables for the project
├── .gitignore                       # Git ignore file
├── config.yaml                      # Configuration file for the project setup
├── dev_notes.md                     # Developer notes for tracking project progress
├── requirements.txt                 # Project dependencies
├── run_robot.py                     # Main script to run the robot
├── todo_list.md                     # Project to-do list for ongoing tasks
├── yolo_experiment.log              # Log file for YOLO training and inference
└── README.md                        # Project documentation (this file)
```

## **Data Collection & Model Training**

- **Custom Dataset Annotation** – Video footage collected across different environments (indoor, outdoor, varied lighting conditions).  
- **Annotation Tool** – **CVAT** for 2D bounding box labeling.  
- **Train/Dev/Test Split**:  
  - **Training Set** – Majority of collected data for fine-tuning.  
  - **Training-Dev Set** – Reserved for hyperparameter tuning and validation.  
  - **Test Set** – Contains only real-world data to ensure reliable evaluation.  

Training is automated via MLflow and integrated into a CI/CD pipeline, ensuring seamless model versioning and retraining.

## **Hardware & Movement**

- **Processing:** **Raspberry Pi 5** + **HAiLO AI Hat+**  
- **Navigation:** **Omni-wheel drive** system for smooth, multidirectional movement  
- **Object Detection:** **YOLOv8n model** optimized for edge computing  
- **Sensors:** **Ultrasonic & LIDAR** for obstacle detection and navigation  
- **Motor Control:** **TB6612 motor drivers** for precise movement  

### **Movement Synchronization**

- **Programmed robot movement** for approaching and retrieving tennis balls  
- **Collision avoidance using sensors** integrated with FastAPI control logic  
- **YOLO model + sensor fusion** to improve movement decisions  
- **Failsafe mechanisms** (stopping if detection fails or unexpected obstacles appear)  

## **Evaluation Metrics**

The model is optimized for:  

- **mAP@0.5** (Mean Average Precision) – Ensures accurate object detection.  
- **Latency (≥20 FPS / ≤50ms per frame)** – Enables real-time execution.  
- **Precision (≥90%) & Recall (≥85%)** – Balances accuracy and efficiency.  

## **Real-Time Inference Monitoring**

To monitor performance on the **Raspberry Pi 5 + HAiLO AI Hat+**, the project integrates **Prometheus** and **Grafana**:

- **Prometheus** – Collects real-time inference metrics (FPS, latency, accuracy, sensor feedback).  
- **Grafana** – Visualizes system telemetry and model performance with real-time dashboards.  

### **Live Dashboard Example**

- **YOLO Inference Speed (FPS)**
- **Latency per Frame**
- **Detected Objects & Confidence Scores**
- **Motor Speed & Sensor Readings**
- **System Temperature & Power Usage**

## **Remote Access & Hosting**

Tennis Ball Bot is accessible remotely via **Cloudflare Tunnel**, allowing for secure monitoring and control.

- **FastAPI API:** Exposes endpoints for live video streaming and telemetry data.
- **Grafana Dashboards:** Hosted remotely for real-time data visualization.
- **Cloudflare Tunnel:** Enables secure, public access without exposing Raspberry Pi to the internet.

## **Automated Retraining & CI/CD**

- **MLflow** – Tracks model versions and logs performance metrics.  
- **GitHub Actions** – Automates testing, training, and deployment.  
- **Automated Model Deployment** – New models are validated and deployed to Raspberry Pi when performance improves.  
- **Versioning & Rollback Support** – Ensures seamless updates while maintaining previous models.  
