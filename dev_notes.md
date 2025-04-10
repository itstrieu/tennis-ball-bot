# 🧠 Project Overview: Tennis Ball Tracking Robot

This project enables a Raspberry Pi robot with omnidirectional wheels to detect and follow a tennis ball using a trained YOLO model, ultrasonic sensors, and motion control logic.

---

## 📂 app/
**robot_controller.py**  
- Entry point for robot logic loop  
- Coordinates detection, decision-making, and motor movement

---

## 📂 core/

### 🧭 navigation/
**motion_controller.py**  
- Controls omnidirectional wheel movement using lgpio  
- Methods for forward, backward, strafe, rotate, stop

**encoders.py**  
- Interface to track motor rotations  
- Will help with precise motion planning

---

### 🧠 strategy/
**movement_decider.py**  
- Contains logic to decide movement direction and speed  
- Uses bounding box area and offset from center  
- Future: integrate ultrasonic override and encoder feedback

---

### 🎯 detection/
**yolo_inference.py**  
- Loads YOLOv5 or YOLOv8 model  
- Detects tennis ball and returns bounding box and confidence

---

### 📡 sensors/
**ultrasonic_sensor.py**  
- Reads front distance using ultrasonic sensor  
- Safety override if too close to object

---

## 📂 config/
**constants.py**  
- Pin mappings for motors, sensors  
- Movement speed constants  
- Target area, center zone threshold  
- Camera offset settings

---

## 📂 training/
- YOLO training and error analysis utilities  
- Only used during model development

Files:
- `train.py`, `analyze_errors.py`, `yolo_inference.py` (shared), `yolo11n.pt`

---

## 📂 utils/
**logger.py**  
- Central logging utility for all modules  
- Use for debugging, event tracking

---

## 🚀 run_robot.py
- Bootstraps and runs `RobotController`  
- Instantiates all components with injected dependencies
