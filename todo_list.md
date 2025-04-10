# ✅ Robot Project – To-Do List

---

## 1. Set Up Cloudflare Tunnel (Remote Access)

- [x] Researched domain hosting options  
- [ ] Install Cloudflare Tunnel on Raspberry Pi  
- [ ] Authenticate and create a tunnel for FastAPI  
- [ ] Create additional tunnels for Grafana and Prometheus  
- [ ] Start tunnels and verify public URLs for each service  

---

## 2. Deploy FastAPI API and Live Metrics

- [x] Tested FastAPI with the model from the test training  
- [ ] Modify FastAPI to serve `/metrics` for Prometheus  
- [ ] Ensure video stream endpoint (`/video_feed`) is accessible  
- [ ] Test FastAPI endpoints locally before exposing them online  

---

## 3. Configure Prometheus (Data Collection)

- [x] Learned how to use Prometheus and built a test setup  
- [ ] Install Prometheus on Raspberry Pi  
- [ ] Configure Prometheus to scrape FastAPI metrics  
- [ ] Verify that Prometheus is correctly collecting and storing data  

---

## 4. Set Up Grafana (Visualization)

- [x] Learned how to use Grafana and built a test dashboard with data from my PC  
- [ ] Install Grafana on Raspberry Pi or cloud instance  
- [ ] Connect Grafana to Prometheus as a data source  
- [ ] Create a Grafana dashboard to visualize YOLO inference stats (e.g., FPS, detection confidence)  
- [ ] Ensure real-time data updates in the Grafana dashboard  

---

## 5. Integrate Cloudflare for Secure Hosting

- [ ] Expose FastAPI (`fastapi.yourdomain.com`)  
- [ ] Expose Grafana (`grafana.yourdomain.com`)  
- [ ] Expose Prometheus (`prometheus.yourdomain.com`)  
- [ ] Test remote accessibility of all services via Cloudflare Tunnel  

---

## 6. Fine-Tune the Model Using the Full Dataset

- [x] Prepared training script with MLflow  
- [x] Ran test training as a sanity check and reviewed results on MLflow  
- [x] Collected and annotated realistic, varied videos for the dataset  
- [x] Update training script to handle a larger dataset  
- [x] Run training for multiple epochs and conduct error analysis  
- [ ] Compare results with initial test training and refine hyperparameters  
- [ ] Tag and version the final dataset (e.g., `v1.0`) for reproducibility  
- [ ] Log training configs (batch size, epochs, augmentations) into MLflow  
- [ ] Document key takeaways from error analysis (patterns, failure cases)  
- [ ] Validate final model on a holdout/test split not seen during training  
- [ ] Export evaluation report (e.g., precision, recall, confusion matrix)  

---

## 7. Optimize YOLO Model for HAiLO AI Hat+ (HEF Format)

- [ ] Convert trained YOLO model to **ONNX format**  
- [ ] Optimize ONNX model using **Hailo Model Zoo** tools  
- [ ] Apply **quantization** to reduce model size while maintaining accuracy  
- [ ] Convert optimized model to **HEF (HAiLO Executable Format)**  
- [ ] Test HEF model inference on HAiLO AI Hat+  
- [ ] Benchmark performance (FPS, latency, accuracy) before and after optimization  
- [ ] Ensure model is **compatible with edge deployment constraints**  

---

## 8. Modularize and Structure Robot Codebase (Expanded)

### 8.1 Refactor Robot Control Code into Clean Module Structure

- [x] Move motor control code into `core/navigation/motion_controller.py`
- [x] Move detection logic into `core/detection/vision_tracker.py`
- [x] Move decision logic into `core/strategy/movement_decider.py`
- [ ] Move ultrasonic logic into `core/sensors/ultrasonic_sensor.py`
- [ ] Remove any duplicated logic in `run_robot.py` or top-level scripts
- [x] Test-import each module to verify it's wired correctly
- [ ] Refine decision logic in movement_decider.py

### 8.2 Add Camera Offset Handling in `VisionTracker`

- [x] Add `camera_offset` parameter to `VisionTracker.__init__()`
- [x] In method that calculates center offset, subtract or add the offset
- [x] Add a test method to print adjusted center values
- [ ] Test with a known frame to verify alignment is correct

### 8.3 Create `RobotController` Class to Orchestrate Everything

- [x] Create file: `app/robot_controller.py`
- [x] Add `__init__()` that takes motion, vision, strategy, sensors
- [x] Add `run()` method to loop:
  - [x] Capture camera frame
  - [x] Detect ball
  - [x] Decide movement
  - [x] Check sensors
  - [x] Send movement commands
- [x] Add graceful shutdown and logging

### 8.4 Ensure Each Class Follows SRP & Allows Dependency Injection

- [x] Refactor all classes to avoid global variables (e.g., model paths, GPIO pins)
- [x] Pass in all configuration via constructors
- [x] Make `MotionController` receive `lgpio_handle` + `motor_pins`
- [x] Make `VisionTracker` receive `model`, `frame_width`, and `camera_offset`
- [x] Make all classes testable with mock data

### 8.5 Write `dev_notes.md` for Module Responsibilities

- [x] Create `dev_notes.md` in `src/`
- [ ] For each module (`motion_controller`, `vision_tracker`, etc.):
  - [ ] Describe its purpose in 1–2 sentences
  - [ ] List public methods
- [ ] Add update checklist at the top of the file

---

## 9. Implement Automated Retraining Pipeline

- [ ] Store new labeled detection data for future retraining  
- [ ] Automate model training when enough new data is collected  
- [ ] Validate model accuracy and only deploy updates if performance improves  
- [ ] Deploy updated model to Raspberry Pi automatically and roll back if needed  

---

## 10. Set Up CI/CD Using GitHub Actions

- [ ] Create a workflow to automatically test scripts on every push  
- [ ] Automate model training execution in the cloud  
- [ ] Deploy trained model to Raspberry Pi when retraining completes  
- [ ] Restart FastAPI service upon model deployment  
- [ ] Ensure model versioning, rollback functionality, and deployment logs  
- [ ] Run automated tests post-deployment to verify functionality  

---

## 11. Test and Optimize Hardware Components

- [x] Tested motors for the wheels  
- [x] Tested motor for the rotating cylinder  
- [ ] Optimize motor control for efficiency, responsiveness, and reliability  
- [ ] Test Raspberry Pi power management and overheating prevention  
- [ ] Ensure all hardware components work under real-world conditions  

---

## 12. Program and Sync Robot Functionality (Expanded)

### 12.1 Program Basic Robot Navigation

- [x] Implement `move_forward`, `move_backward`, `strafe_left`, `strafe_right`, `rotate_left`, `rotate_right`, `stop` in `MotionController`
- [ ] Add logging inside each method to confirm calls
- [ ] Manually test each direction one-by-one

### 12.2 Program and Test Onboard Sensors

- [ ] Implement `read_distance()` and `is_obstacle_close()` in `UltrasonicSensor`
- [ ] Print distance value periodically in isolation
- [ ] Confirm reliable readings at various object distances

### 12.3 Sync Movement with YOLO Detection

- [x] In `VisionTracker`, return bounding box center & area
- [x] In `MovementDecider`, decide:
  - [x] Direction: left / right / center
  - [x] Distance action: move / stop / back
- [x] In `RobotController`, pass detection result to decision logic
- [x] Based on decision, call corresponding movement method

### 12.4 Sync Movement with Sensor Input

- [ ] In `RobotController`, read ultrasonic distance
- [ ] Override movement if distance is below threshold
- [ ] Add log line when override triggers

### 12.5 Implement Failsafe Mechanism

- [x] Add counter for consecutive frames with no detection
- [x] If above threshold (e.g. 10 frames), stop movement
- [x] Reset counter when object is detected again

---

## 13. Add Remote Streaming and Monitoring Features

- [ ] Create `streaming/` module:
  - `camera_streamer.py` – JPEG frame capture  
  - `performance_monitor.py` – system metrics  
  - `stream_client.py` – sends data to server  
- [ ] Stream annotated camera frames via WebSocket or MJPEG  
- [ ] Send periodic metrics to FastAPI endpoint  
- [ ] Coordinate from within `RobotController`  

---

## 14. (Optional) Build Custom React Frontend

- [ ] Create a React app to display live video feed and real-time stats  
- [ ] Deploy React frontend to Cloudflare Pages  
- [ ] Connect React frontend to FastAPI and Grafana APIs  
- [ ] Ensure seamless real-time data updates in the UI  
- [ ] Optimize frontend for low latency and smooth visualization  
