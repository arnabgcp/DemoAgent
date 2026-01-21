import os
import json
from fastapi import FastAPI, HTTPException, BackgroundTasks
from google.cloud import logging
from google.cloud import aiplatform
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from kubernetes import client, config
import asyncio

# --- Configuration (Update these details) ---
PROJECT_ID = "your-gcp-project-id"
K8S_DEPLOYMENT_NAME = "your-deployment-name" 
K8S_NAMESPACE = "default"
# -------------------------------------------

os.environ["GOOGLE_CLOUD_PROJECT"] = PROJECT_ID

app = FastAPI(
    title="K8s Auto-Scaling Agent API",
    description="An API that uses an AI agent to read GCP logs and scale K8s pods."
)

# Initialize clients (can be done on startup using FastAPI lifespan events for cleaner state management)
logging_client = logging.Client(project=PROJECT_ID)
aiplatform.init(project=PROJECT_ID)
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

def read_error_logs(log_filter="severity=ERROR", max_entries=5):
    """Reads recent error logs from Google Cloud Logging."""
    print(f"Reading up to {max_entries} logs with filter: '{log_filter}'")
    entries = logging_client.list_entries(filter_=log_filter, max_size=max_entries)
    log_data = []
    for entry in entries:
        log_data.append({
            "timestamp": entry.timestamp.isoformat(),
            "severity": entry.severity,
            "message": entry.payload,
            "resource": entry.resource.type
        })
    return log_data

def scale_k8s_deployment(replicas: int):
    """Scales a Kubernetes deployment to the specified number of replicas."""
    print(f"Attempting to scale deployment '{K8S_DEPLOYMENT_NAME}' to {replicas} replicas...")
    try:
        # Load Kubernetes configuration (ensure permissions are set for the environment)
        config.load_kube_config() 
        apps_v1 = client.AppsV1Api()
        
        scale_body = client.V1Scale(
            spec=client.V1ScaleSpec(replicas=replicas)
        )
        
        api_response = apps_v1.patch_namespaced_deployment_scale(
            name=K8S_DEPLOYMENT_NAME,
            namespace=K8S_NAMESPACE,
            body=scale_body
        )
        print(f"Deployment scaled successfully. Current replicas: {api_response.status.replicas}")
        return f"Scaled to {api_response.status.replicas} replicas."
    except client.ApiException as e:
        print(f"Exception when calling AppsV1Api->patch_namespaced_deployment_scale: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_logs_and_act():
    """The main agentic logic run in the background."""
    # This is an async function to avoid blocking the API server while the LLM runs
    logs = read_error_logs(max_entries=20)
    if not logs:
        return "No logs to process."

    logs_str = json.dumps(logs, indent=2)
    system_prompt = (
        "You are an autonomous AI agent monitoring Google Cloud Platform logs for a Kubernetes application. "
        "Analyze the logs and determine if the Kubernetes deployment needs scaling. "
        "If needed, output JSON: {'action': 'scale', 'replicas': <number>}. "
        "If not, output JSON: {'action': 'none'}. Only output the JSON object."
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Analyze the following logs and suggest an action:\n\n{logs_str}")
    ]
    
    # Run the LLM call asynchronously
    response = await asyncio.to_thread(llm.invoke, messages)
    
    try:
        action_plan = json.loads(response.content.strip())
        if action_plan.get("action") == "scale" and isinstance(action_plan.get("replicas"), int):
            scale_k8s_deployment(action_plan["replicas"])
            return f"Agent decided to scale to {action_plan['replicas']} replicas."
        elif action_plan.get("action") == "none":
            return "Agent decided no action was necessary."
        else:
            return "Agent returned an invalid action plan format."
            
    except json.JSONDecodeError:
        return f"Could not decode JSON response from LLM: {response.content}"


@app.get("/healthz")
def health_check():
    """Health check endpoint for the API."""
    return {"status": "healthy"}

@app.post("/trigger-scaling")
async def trigger_agent_action(background_tasks: BackgroundTasks):
    """
    Triggers the AI agent to read GCP logs and potentially scale the K8s deployment.
    Runs the agent logic in a background task to return a quick response.
    """
    background_tasks.add_task(process_logs_and_act)
    return {"message": "Log analysis and potential scaling action triggered in the background."}

@app.post("/scale-manual/{replicas}")
def manual_scale(replicas: int):
    """Allows manual scaling of the deployment."""
    result = scale_k8s_deployment(replicas)
    return {"message": result}