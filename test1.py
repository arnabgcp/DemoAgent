
from kubernetes import client, config

def rollback_deployment(deployment_name, namespace="default"):
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

    # try:
    #     apps_v1.patch_namespaced_deployment(deployment_name, namespace, patch_body)
    #     print(f"Successfully rolled back '{deployment_name}' to previous revision.")
    # except Exception as e:
    #     print(f"Failed to patch deployment: {e}")

if __name__ == "__main__":
    rollback_deployment("nginx")