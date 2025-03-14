**Structured Study Plan for Designing Machine Learning Systems (Chip Huyen)**

### **Goal:** Learn to design and deploy scalable, production-ready ML systems while improving software engineering skills, with a focus on applying these concepts to the **tennis ball retrieval robot project**.

### **Timeline:** 6 weeks

---

## **Week 1: Understanding ML in Production**
**Read:** Chapters 1-3  
**Key Concepts:**  
- Differences between research ML and production ML  
- Challenges in deploying ML models (data drift, feedback loops)  
- Model deployment strategies (batch vs. online inference)  

**Hands-on Task (Tennis Ball Bot):**  
- Define the **ML workflow for the robot**, from camera input to decision-making.  
- Set up a **Flask or FastAPI** service that loads a trained model for ball detection and serves predictions via an API.  

---

## **Week 2: Data Engineering for ML Systems**
**Read:** Chapters 4-5  
**Key Concepts:**  
- Designing feature stores  
- Handling large-scale data pipelines  
- Streaming vs. batch processing  

**Hands-on Task (Tennis Ball Bot):**  
- Collect and process video data from the robot’s camera.  
- Use **Pandas or OpenCV** to preprocess frames and extract useful features.  
- Store labeled data in a simple SQLite or PostgreSQL database for training.  

---

## **Week 3: ML Pipelines & Automation**
**Read:** Chapters 6-7  
**Key Concepts:**  
- Automating ML workflows  
- Versioning models and data  
- Orchestration tools (Airflow, Prefect, Kubeflow)  

**Hands-on Task (Tennis Ball Bot):**  
- Build an **automated training pipeline** to retrain the ball detection model as new data arrives.  
- Implement model versioning with **DVC or MLflow** to track performance over time.  

---

## **Week 4: Model Deployment & Serving**
**Read:** Chapters 8-9  
**Key Concepts:**  
- Model serving architectures  
- Latency vs. throughput trade-offs  
- Deploying models with containers and cloud services  

**Hands-on Task (Tennis Ball Bot):**  
- Deploy the trained ball detection model using **Docker** and serve it via **FastAPI**.  
- Integrate the model with the robot’s control system to make real-time movement decisions.  

---

## **Week 5: Monitoring & Reliability**
**Read:** Chapters 10-11  
**Key Concepts:**  
- Monitoring ML models in production  
- Handling model decay and drift  
- Retraining strategies  

**Hands-on Task (Tennis Ball Bot):**  
- Implement **basic monitoring** to track model confidence and error rates over time.  
- Write a script that detects changes in lighting conditions and adjusts preprocessing steps dynamically.  

---

## **Week 6: Scaling & Designing ML Systems**
**Read:** Chapters 12-13  
**Key Concepts:**  
- Scaling ML infrastructure  
- Designing end-to-end ML architectures  
- Case studies of real-world ML deployments  

**Hands-on Task (Tennis Ball Bot):**  
- Sketch an **end-to-end system design** for the robot, from data ingestion to model serving.  
- Optimize processing for real-time performance by improving the inference pipeline.  

---

## **Final Project: Apply Everything**
- Fully integrate **data ingestion → training pipeline → model serving → monitoring** into the tennis ball retrieval robot.  
- Deploy the system on a **Raspberry Pi or embedded device** for real-world testing.  
- Document the design and architecture as if presenting it to an engineering team.  