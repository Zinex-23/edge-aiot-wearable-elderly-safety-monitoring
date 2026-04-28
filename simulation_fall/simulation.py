import os
import time
import random
import threading
import psutil
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

# Global state for simulation
simulation_state = {
    'samples': [],
    'current_prediction': 'Waiting...',
    'current_ground_truth': 'Waiting...',
    'is_correct': None, # True, False, or None
    'total_predictions': 0,
    'correct_predictions': 0,
    'accuracy': 0.0,
    'ram_usage': 0.0,
    'cpu_usage': 0.0,
    'flash_usage': 0.0,
    'inference_latency_ms': 0.0,
    'fps': 0.0,
    'energy_mJ': 0.0,
    'events': []
}

class MockModel:
    """Mock model to be replaced with actual inference code later."""
    def predict(self, window):
        # A real model would convert the 100x6 array into a tensor here
        # E.g. interpreter.set_tensor(input_details[0]['index'], window)
        
        # Simulate processing time (e.g. 5ms to 20ms)
        time.sleep(random.uniform(0.005, 0.020))
        
        # Dummy logic: mostly correct prediction based on injected ground truth for visual completeness
        # In actual usage, it would just predict from 'window'
        return random.choices(['fall', 'non_fall'], weights=[0.2, 0.8])[0]

model = MockModel()

def simulate_data_stream():
    """Generates 50Hz IMU samples and performs inference every 100 samples."""
    global simulation_state
    global is_fall_mode
    
    while True:
        # Determine ground_truth based on toggle
        ground_truth = 'fall' if is_fall_mode else 'non_fall'
            
        simulation_state['current_ground_truth'] = ground_truth
        simulation_state['current_prediction'] = 'Sampling...'
        simulation_state['is_correct'] = None
        
        window = []
        start_time_window = time.time()
        
        # 100 samples = 2 seconds at 50Hz
        for i in range(100):
            sample_start = time.time()
            
            if not is_fall_mode:
                # Normal activity (walking/standing)
                sample = {
                    'timestamp_ms': int(sample_start * 1000),
                    'acc_x': random.uniform(-0.1, 0.1),
                    'acc_y': random.uniform(-0.1, 0.1),
                    'acc_z': 1.0 + random.uniform(-0.1, 0.1), # Gravity
                    'gyro_x': random.uniform(-10, 10),
                    'gyro_y': random.uniform(-10, 10),
                    'gyro_z': random.uniform(-10, 10)
                }
            else:
                # Continuous Fall state (high amplitude anomaly)
                sample = {
                    'timestamp_ms': int(sample_start * 1000),
                    'acc_x': random.uniform(-4.0, 4.0),
                    'acc_y': random.uniform(-4.0, 4.0),
                    'acc_z': random.uniform(-5.0, 6.0),
                    'gyro_x': random.uniform(-250, 250),
                    'gyro_y': random.uniform(-250, 250),
                    'gyro_z': random.uniform(-250, 250)
                }
                
            window.append(sample)
            
            # Update state with the sliding window
            simulation_state['samples'] = window
            
            # Enforce 50Hz (0.02s interval)
            elapsed = time.time() - sample_start
            sleep_time = max(0.0, 0.02 - elapsed)
            time.sleep(sleep_time)
            
        # Inference Stage
        inference_start = time.time()
        # Mocking the model getting the true ground truth occasionally to simulate high accuracy
        # In reality, predict(window) should not know ground truth.
        raw_prediction = model.predict(window)
        
        # Force a prediction that aligns 90% with ground truth for demo
        is_mock_correct = random.random() < 0.9
        prediction = ground_truth if is_mock_correct else raw_prediction
        
        inference_time = time.time() - inference_start
        latency_ms = inference_time * 1000.0
        fps = 100.0 / (time.time() - start_time_window)
        
        # Energy simulation: Roughly 30 mW active power on ESP32 running inference
        energy_est = 30.0 * inference_time # mJ
        
        is_correct = (prediction == ground_truth)
        
        # Update metrics safely
        simulation_state['total_predictions'] += 1
        if is_correct:
            simulation_state['correct_predictions'] += 1
            
        acc = (simulation_state['correct_predictions'] / simulation_state['total_predictions']) * 100.0
        
        simulation_state['current_prediction'] = prediction
        simulation_state['is_correct'] = is_correct
        simulation_state['accuracy'] = acc
        simulation_state['inference_latency_ms'] = latency_ms
        simulation_state['fps'] = fps
        simulation_state['energy_mJ'] = energy_est
        
        # Fake ESP32-S3 Super Mini Resource usage (4MB Flash, 512KB SRAM)
        simulation_state['cpu_usage'] = random.uniform(5.5, 12.8)
        simulation_state['ram_usage'] = random.uniform(38.0, 41.5)
        simulation_state['flash_usage'] = 31.5
        
        # Add to event log
        event = {
            'time': time.strftime('%H:%M:%S'),
            'prediction': prediction,
            'ground_truth': ground_truth,
            'correct': is_correct,
            'latency_ms': f"{latency_ms:.1f}",
            'energy_mJ': f"{energy_est:.2f}"
        }
        simulation_state['events'].insert(0, event)
        if len(simulation_state['events']) > 20:
            simulation_state['events'].pop()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    return jsonify(simulation_state)

is_fall_mode = False
@app.route('/api/toggle_mode', methods=['POST'])
def toggle_mode():
    global is_fall_mode
    is_fall_mode = request.json.get('is_fall_mode', False)
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    print("Starting Fall Detection Simulation Dashboard at http://localhost:8080")
    t = threading.Thread(target=simulate_data_stream, daemon=True)
    t.start()
    app.run(host='0.0.0.0', port=8080, debug=True, use_reloader=False)
