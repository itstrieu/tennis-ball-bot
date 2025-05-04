# 🧠 Project Overview: Tennis Ball Tracking Robot

This project enables a Raspberry Pi robot with omnidirectional wheels to detect and follow a tennis ball using a trained YOLO model, ultrasonic sensors, and motion control logic.

## 🛠️ Development Setup
- Python 3.8+ required
- Dependencies managed via `requirements.txt`
- Uses Picamera2 for camera operations
- FastAPI for optional streaming server
- YOLOv8 for object detection

---

## 📂 app/
**robot_controller.py**  
- Entry point for robot logic loop  
- Coordinates detection, decision-making, and motor movement  
- Improved error handling and cleanup logic
- Uses async/await for non-blocking operations

**camera_manager.py**  
- Manages camera and frame capture operations  
- Handles frame updates and provides access to the latest frame  
- Optional streaming support
- Thread-safe frame queue implementation

---

## 📂 core/

### 🧭 navigation/
**motion_controller.py**  
- Controls omnidirectional wheel movement using lgpio  
- Methods for forward, backward, strafe, rotate, stop
- Implements safety checks and emergency stop

**encoders.py**  
- Interface to track motor rotations  
- Will help with precise motion planning
- Future: integrate with motion controller for closed-loop control

---

### 🧠 strategy/
**movement_decider.py**  
- Contains logic to decide movement direction and speed  
- Uses bounding box area and offset from center  
- Future: integrate ultrasonic override and encoder feedback
- Implements PID-like control for smooth movement

---

### 🎯 detection/
**yolo_inference.py**  
- Loads YOLOv5 or YOLOv8 model  
- Detects tennis ball and returns bounding box and confidence
- Optimized for real-time performance on Raspberry Pi

---

### 📡 sensors/
**ultrasonic_sensor.py**  
- Reads front distance using ultrasonic sensor  
- Safety override if too close to object
- Configurable distance thresholds

---

## 📂 config/
**constants.py**  
- Pin mappings for motors, sensors  
- Movement speed constants  
- Target area, center zone threshold  
- Camera offset settings
- Safety thresholds and timeouts

---

## 📂 training/
- YOLO training and error analysis utilities  
- Only used during model development
- Includes data collection and preprocessing scripts

Files:
- `train.py`, `analyze_errors.py`, `yolo_inference.py` (shared), `yolo11n.pt`
- Training data and model checkpoints stored separately

---

## 📂 utils/
**logger.py**  
- Central logging utility for all modules  
- Use for debugging, event tracking
- Configurable log levels and output formats

---

## 📂 streaming/
**stream_server.py**  
- FastAPI server for streaming camera feed and providing debug information  
- Handles WebSocket connections for real-time video streaming  
- Optional feature that does not interfere with core robot operation
- Includes debug overlay and control interface

---

## 🚀 run_robot.py
- Bootstraps and runs `RobotController`  
- Instantiates all components with injected dependencies
- Handles graceful shutdown and cleanup
- Configurable startup options

---

## 📝 Notes
- The project now supports optional streaming via FastAPI and WebSocket.
- Improved error handling and cleanup logic across all components.
- Modular structure allows for easy extension and maintenance.
- All components are designed to work independently or together.
- Extensive logging for debugging and monitoring.
- Future improvements planned for encoder integration and PID control.

## 🔄 Development Workflow
1. Code changes should be tested on the robot hardware
2. Use logging for debugging and monitoring
3. Keep streaming server optional to maintain core functionality
4. Follow the modular structure for new features
5. Update documentation when adding new components
