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

def read_error_logs(log_filter, max_entries=100):
    """Reads recent error logs from Google Cloud Logging."""
    print(f"Reading up to {max_entries} logs with filter: '{log_filter}'")
    entries = logging_client.list_entries(filter_=log_filter, max_results=max_entries)
    log_data = []
    for entry in entries:
        log_data.append({
            "timestamp": entry.timestamp.isoformat(),
            "severity": entry.severity,
            "message": entry.payload,
            "app": entry.labels.get("k8s-pod/app", "Unknown"),
            "resource": entry.resource.type,
        })
    return log_data

def rollback_k8s_deployment(deployment_name, namespace="default"):
    # Authenticate to GKE
    config.load_kube_config()
    apps_v1 = client.AppsV1Api()

    # 1. Find all ReplicaSets for the deployment
    # Ensure label_selector matches your deployment labels
    label_selector = f"app={deployment_name}" 
    rs_list = apps_v1.list_namespaced_replica_set(
        namespace, 
        label_selector=label_selector
    ).items

    # 2. Sort by creation time (descending) to find the previous one
    rs_list.sort(key=lambda x: x.metadata.creation_timestamp, reverse=True)

    if len(rs_list) < 2:
        print("Error: No previous revision found in history.")
        return
    print(rs_list[1])
    # rs_list[0] is the current revision, rs_list[1] is the previous one
    previous_rs = rs_list[1]
    prev_template = previous_rs.spec.template

    # 3. Patch the deployment with the previous template
    # This effectively performs a "rollout undo"
    patch_body = {
        "spec": {
            "template": {
                "spec": prev_template.spec
            }
        }
    }

    try:
        apps_v1.patch_namespaced_deployment(deployment_name, namespace, patch_body)
        print(f"Successfully rolled back '{deployment_name}' to previous revision.")
    except Exception as e:
        print(f"Failed to patch deployment: {e}")

def agentic_action(logs):
    """Agentic AI that analyzes logs and decides on scaling actions."""
    if not logs:
        print("No logs to process.")
        return

    logs_str = json.dumps(logs, indent=2)

    print(logs_str)
    
    system_prompt = (
        "You are an autonomous AI agent monitoring Google Cloud Platform logs for a Kubernetes application. "
        "Your task is to analyze the provided log entries and determine if the Kubernetes deployment needs roll back or not. Deploymentname is the app name "
        "If there is more error in the logs than, it should suggest action as rollback, If action is needed, output a JSON object with 'action': 'roll back', 'deployment name': ''"
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
        print(action_plan["deployment name"])

        if action_plan.get("action") == "roll back" :
            rollback_k8s_deployment(action_plan["deployment name"])
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
    one_hour_ago = now - timedelta(hours=1)

    #filter = "severity=ERROR AND resource.type=k8s_container AND nginx AND not found AND TIMESTAMP >= " + '"{}"'.format(one_hour_ago.strftime("%Y-%m-%dT%H:%M:%S"))
    
    filter = "nginx-test"
    error_logs = read_error_logs(log_filter=filter , max_entries=20)
    print(error_logs)
    agentic_action(error_logs)