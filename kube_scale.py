from dotenv import load_dotenv
import os
import json
from google.cloud import logging
from google.cloud import aiplatform
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from kubernetes import client, config
import time
from datetime import datetime, timedelta

# --- Configuration ---
PROJECT_ID = "wayfair-test-378605"
K8S_DEPLOYMENT_NAME = "nginx" # e.g., "nginx-deployment"
K8S_NAMESPACE = "default"
# ---------------------

# Load environment variables from .env file
load_dotenv()

os.environ["GOOGLE_CLOUD_PROJECT"] = PROJECT_ID

# Initialize logging client
logging_client = logging.Client(project=PROJECT_ID)

# Initialize the LLM (using Gemini as an example)
aiplatform.init(project=PROJECT_ID)

api_key = os.getenv("GOOGLE_API_KEY")
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key="AIzaSyDHBKR7iFDGhs3o8-kezQP9Phs23MV5Tfs")

def read_error_logs(log_filter, max_entries=5):
    """Reads recent error logs from Google Cloud Logging."""
    print(f"Reading up to {max_entries} logs with filter: '{log_filter}'")
    entries = logging_client.list_entries(filter_=log_filter, max_results=max_entries)
    log_data = []
    for entry in entries:
        log_data.append({
            "timestamp": entry.timestamp.isoformat(),
            "severity": entry.severity,
            "message": entry.payload,
            "resource": entry.resource.type
        })
    return log_data

def scale_k8s_deployment(replicas):
    """Scales a Kubernetes deployment to the specified number of replicas."""
    print(f"Attempting to scale deployment '{K8S_DEPLOYMENT_NAME}' to {replicas} replicas...")
    try:
        # Load Kubernetes configuration (handles local kubeconfig or in-cluster service account)
        config.load_kube_config() # or config.load_incluster_config()
        
        apps_v1 = client.AppsV1Api()
        
        # Create a V1Scale body object with the desired replica count
        scale_body = client.V1Scale(
            spec=client.V1ScaleSpec(replicas=replicas)
        )
        
        # Patch the deployment's scale subresource
        api_response = apps_v1.patch_namespaced_deployment_scale(
            name=K8S_DEPLOYMENT_NAME,
            namespace=K8S_NAMESPACE,
            body=scale_body
        )
        print(f"Deployment scaled successfully. Current replicas: **{api_response.status.replicas}**")
    except client.ApiException as e:
        print(f"Exception when calling AppsV1Api->patch_namespaced_deployment_scale: {e}")
        raise

def agentic_action(logs):
    """Agentic AI that analyzes logs and decides on scaling actions."""
    if not logs:
        print("No logs to process.")
        return

    logs_str = json.dumps(logs, indent=2)

    print(logs_str)
    
    system_prompt = (
        "You are an autonomous AI agent monitoring Google Cloud Platform logs for a Kubernetes application. "
        "Your task is to analyze the provided log entries and determine if the Kubernetes deployment needs scaling. "
        "Current deployment has 3 replicas already "
        "If scaling is needed, output a JSON object with 'action': 'scale', 'replicas': <number>. "
        "If no action is needed, output a JSON object with 'action': 'none'."
        "Only output the JSON object, nothing else. remove all header like ```json."
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Analyze the following logs and suggest an action:\n\n{logs_str}")
    ]

    response = llm.invoke(messages)
    
    print(response.content)


    # The 'decide' and 'act' part of the agent
    try:
        action_plan = json.loads(response.content.strip())
        print("\n--- Agent's Action Plan ---")
        print(json.dumps(action_plan, indent=2))
        print("---------------------------\n")

        if action_plan.get("action") == "scale" and isinstance(action_plan.get("replicas"), int):
            scale_k8s_deployment(action_plan["replicas"])
        elif action_plan.get("action") == "none":
            print("Agent decided no scaling action was necessary.")
        else:
            print("Agent returned an invalid action plan format.")
            
    except json.JSONDecodeError:
        print(f"Could not decode JSON response from LLM: {response.content}")

# Main execution
if __name__ == "__main__":
    # Ensure your K8s cluster and deployment details are updated in the Configuration section above
    # The script will run the logic once. For continuous operation, wrap in a loop or deploy as a cron job/operator.
    

    # Get current datetime
    now = datetime.now()

    # Subtract one hour
    one_hour_ago = now - timedelta(hours=2)

    filter = "severity=ERROR AND resource.type=k8s_container AND TIMESTAMP >= " + '"{}"'.format(one_hour_ago.strftime("%Y-%m-%dT%H:%M:%S"))
    error_logs = read_error_logs(log_filter=filter , max_entries=20)
    #print(error_logs)
    agentic_action(error_logs)