from kubernetes import client, config

def rollback_k8s_deployment(deployment_name, namespace="default", revision=0):
    """
    Rolls back a Kubernetes deployment to a specific revision using the Python client.
    
    :param deployment_name: The name of the Kubernetes deployment.
    :param namespace: The namespace where the deployment is located.
    :param revision: The target revision number to roll back to (0 for the previous revision).
    """
    try:
        # Load Kubernetes configuration from default location (e.g., ~/.kube/config)
        config.load_kube_config()

        # Create an API client instance
        api_instance = client.AppsV1Api()
        
        # Define the rollback configuration
        # Note: The DeploymentRollback object and create_namespaced_deployment_rollback
        # method are often associated with older API versions (e.g., AppsV1beta1).
        # For modern K8s/GKE (v1.16+), rolling back is done by patching the deployment
        # to the desired revision from history, or simply using the 'undo' equivalent.
        # The recommended approach in Python involves using the built-in 'kubectl rollout undo' logic.

        # Modern K8s API approach to "undo" the last rollout (equivalent to `kubectl rollout undo`)
        # This will revert the deployment to its immediately previous state.
        if revision == 0:
            api_instance.patch_namespaced_deployment_rollback(
                name=deployment_name,
                namespace=namespace,
                body={} # Empty body triggers undo to the last revision
            )
            print(f"Deployment '{deployment_name}' in namespace '{namespace}' rolled back to previous revision.")
        
        # Rollback to a specific revision (requires custom logic to apply the old manifest)
        # The `create_namespaced_deployment_rollback` method has been deprecated.
        # To rollback to a specific revision, you'd typically retrieve the manifest 
        # of that revision from the `kubectl rollout history --revision=<rev> -o yaml` 
        # and then apply it using the client.
        else:
            print(f"Direct rollback to specific revision '{revision}' via the API requires manual manifest application logic.")
            print("Consider using `kubectl rollout undo --to-revision=<revision>` command line for this specific scenario.")

    except client.ApiException as e:
        print(f"Error rolling back deployment: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == '__main__':
    # Replace 'my-deployment-name' with your actual deployment name
    # Replace 'my-namespace' if it is not the 'default' namespace
    rollback_k8s_deployment(deployment_name="my-app-deployment", namespace="default")
