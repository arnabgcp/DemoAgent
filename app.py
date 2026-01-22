from flask import Flask, jsonify
import google.cloud.logging
import logging
from kubernetes import client, config

# Create a Flask application instance
app = Flask(__name__)

client = google.cloud.logging.Client()
client.setup_logging()

# Sample data to return from one of the APIs
sample_items = [
    {'id': 1, 'name': 'Item A', 'category': 'Category 1'},
    {'id': 2, 'name': 'Item B', 'category': 'Category 2'}
]

# API Endpoint 1: A simple greeting
@app.route('/', methods=['GET'])
def home():
    return "<p>Hello, World! This is a Flask API V5</p>"

# API Endpoint 2: Return sample data as JSON
@app.route('/api/items', methods=['GET'])
def get_items():
    # Return the data as a JSON response
    return jsonify(sample_items) + sample_var


@app.route('/error-test', methods=['GET'])
def trigger_error():
    try:
        # Intentional error: division by zero
        1 / 0
    except Exception as e:
        # Logs the error and stack trace to GCP Cloud Logging
        logging.exception("An error occurred in the /error-test endpoint: %s", str(e))
        return jsonify({"error": "Internal Server Error"}), 500


@app.errorhandler(Exception)
def handle_exception(e):
    logging.error("Unhandled Exception for nginx-test : %s", str(e), exc_info=True)
    return jsonify({"error": "An unexpected error occurred"}), 500

# Run the application
if __name__ == '__main__':
    # This runs the app on a local development server, accessible at http://127.0.0.1:5000/
    app.run(host='0.0.0.0', port=5000, debug=True)