# Fall Detection Simulation Dashboard

This is a local Python Flask dashboard to simulate fall detection inferences. It mocks a 50Hz sensor stream (6-axis IMU) and executes a mock AI model window every 100 samples (2 seconds).

## Requirements

Ensure you have Python 3 installed. Then, install dependencies:

```bash
pip install -r requirements.txt
```

## Running the Dashboard

Start the local server:

```bash
python simulation.py
```

Then, open your browser and navigate to:
[http://localhost:8080](http://localhost:8080)

## Modifying the Model
Currently, a `MockModel` is used in `simulation.py`. You can replace `MockModel.predict()` with your actual TFLite or Keras model in Python down the line.
