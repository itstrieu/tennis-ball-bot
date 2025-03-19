## To-Do List

### 1. Set Up Cloudflare Tunnel (Remote Access)
- [x] Researched domain hosting options
- [ ] Install Cloudflare Tunnel on Raspberry Pi
- [ ] Authenticate and create a tunnel for FastAPI
- [ ] Create additional tunnels for Grafana and Prometheus
- [ ] Start tunnels and verify public URLs for each service

### 2. Deploy FastAPI API and Live Metrics
- [x] Tested FastAPI with the model from the test training
- [ ] Modify FastAPI to serve `/metrics` for Prometheus
- [ ] Ensure video stream endpoint (`/video_feed`) is accessible
- [ ] Test FastAPI endpoints locally before exposing them online

### 3. Configure Prometheus (Data Collection)
- [x] Learned how to use Prometheus and built a test setup
- [ ] Install Prometheus on Raspberry Pi
- [ ] Configure Prometheus to scrape FastAPI metrics
- [ ] Verify that Prometheus is correctly collecting and storing data

### 4. Set Up Grafana (Visualization)
- [x] Learned how to use Grafana and built a test dashboard with data from my PC
- [ ] Install Grafana on Raspberry Pi or cloud instance
- [ ] Connect Grafana to Prometheus as a data source
- [ ] Create a Grafana dashboard to visualize YOLO inference stats (e.g., FPS, detection confidence)
- [ ] Ensure real-time data updates in the Grafana dashboard

### 5. Integrate Cloudflare for Secure Hosting
- [ ] Expose FastAPI (`fastapi.yourdomain.com`)
- [ ] Expose Grafana (`grafana.yourdomain.com`)
- [ ] Expose Prometheus (`prometheus.yourdomain.com`)
- [ ] Test remote accessibility of all services via Cloudflare Tunnel

### 6. Fine-Tune the Model Using the Full Dataset
- [x] Prepared training script with MLflow
- [x] Ran test training as a sanity check and reviewed results on MLflow
- [x] Collected and annotated realistic, varied videos for the dataset
- [x] Update training script to handle a larger dataset
- [ ] Run training for multiple epochs and evaluate model performance
- [ ] Compare results with initial test training and refine hyperparameters

### 7. Optimize YOLO Model for HAiLO AI Hat+ (HEF Format)
- [ ] Convert trained YOLO model to **ONNX format**
- [ ] Optimize ONNX model using **Hailo Model Zoo** tools
- [ ] Apply **quantization** to reduce model size while maintaining accuracy
- [ ] Convert optimized model to **HEF (HAiLO Executable Format)**
- [ ] Test HEF model inference on HAiLO AI Hat+  
- [ ] Benchmark performance (FPS, latency, accuracy) before and after optimization  
- [ ] Ensure model is **compatible with edge deployment constraints**  

### 8. Reorganize the Scripts to Be More Modular (Without ChatGPT)
- [x] Split training script into separate modules
- [ ] Refactor FastAPI endpoints for better structure and maintainability
- [ ] Ensure all scripts work independently but integrate seamlessly
- [ ] Document key functions and scripts for easier debugging

### 9. Implement Automated Retraining Pipeline
- [ ] Store new labeled detection data for future retraining
- [ ] Automate model training when enough new data is collected
- [ ] Validate model accuracy and only deploy updates if performance improves
- [ ] Deploy updated model to Raspberry Pi automatically and roll back if needed

### 10. Set Up CI/CD Using GitHub Actions
- [ ] Create a workflow to automatically test scripts on every push
- [ ] Automate model training execution in the cloud
- [ ] Deploy trained model to Raspberry Pi when retraining completes
- [ ] Restart FastAPI service upon model deployment
- [ ] Ensure model versioning, rollback functionality, and deployment logs
- [ ] Run automated tests post-deployment to verify functionality

### 11. Test and Optimize Hardware Components
- [x] Tested motors for the wheels
- [x] Tested motor for the rotating cylinder
- [ ] Optimize motor control for efficiency, responsiveness, and reliability
- [ ] Test Raspberry Pi power management and overheating prevention
- [ ] Ensure all hardware components work under real-world conditions

### 12. Program and Sync Robot Functionality
- [ ] Program robot movement for basic navigation
- [ ] Program and test the onboard sensors (e.g., obstacle detection, ball detection)
- [ ] Sync movement control with YOLO object detection outputs
- [ ] Sync movement control with sensor input for adaptive navigation
- [ ] Implement failsafe mechanisms (e.g., stopping if object detection fails)

### 13. (If time permits) Build a Custom React Frontend for Monitoring
- [ ] Create a React app to display live video feed and real-time stats
- [ ] Deploy React frontend to Cloudflare Pages
- [ ] Connect React frontend to FastAPI and Grafana APIs
- [ ] Ensure seamless real-time data updates in the UI
- [ ] Optimize frontend for low latency and smooth visualization
