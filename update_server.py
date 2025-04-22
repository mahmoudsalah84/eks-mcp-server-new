#!/usr/bin/env python3
"""
Update the EKS MCP Server with the new SDK implementation
"""

import os
import shutil
import subprocess
import sys

def backup_file(file_path):
    """Backup a file"""
    backup_path = f"{file_path}.bak"
    print(f"Backing up {file_path} to {backup_path}")
    shutil.copy2(file_path, backup_path)

def update_server():
    """Update the server with the new SDK implementation"""
    # Define paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    main_py = os.path.join(base_dir, "main.py")
    aws_auth = os.path.join(base_dir, "aws_auth.py")
    
    # Check if files exist
    if not os.path.exists(main_py):
        print(f"Error: {main_py} not found")
        sys.exit(1)
    
    # Backup files
    backup_file(main_py)
    
    # Copy AWS auth utilities
    if os.path.exists(aws_auth):
        print(f"Copying {aws_auth} to {base_dir}")
        # No need to copy, it's already there
    
    # Update main.py to use the new SDK implementation
    print("Updating main.py to use the new SDK implementation")
    with open(main_py, "r") as f:
        content = f.read()
    
    # Add import for the new SDK implementation
    if "from k8s_operations_sdk_v2 import KubernetesOperationsSDKV2" not in content:
        content = content.replace(
            "from k8s_operations_sdk import KubernetesOperationsSDK",
            "from k8s_operations_sdk import KubernetesOperationsSDK\n# Import the KubernetesOperationsSDKV2 class\nfrom k8s_operations_sdk_v2 import KubernetesOperationsSDKV2"
        )
    
    # Initialize the new SDK implementation
    if "k8s_sdk_v2_ops = KubernetesOperationsSDKV2()" not in content:
        content = content.replace(
            "# Initialize KubernetesOperationsSDK\nk8s_sdk_ops = KubernetesOperationsSDK()",
            "# Initialize KubernetesOperationsSDK\nk8s_sdk_ops = KubernetesOperationsSDK()\n# Initialize KubernetesOperationsSDKV2\nk8s_sdk_v2_ops = KubernetesOperationsSDKV2()"
        )
    
    # Update the handler functions to use the new SDK implementation
    handlers = [
        "handle_list_namespaces",
        "handle_list_pods",
        "handle_describe_pod",
        "handle_get_deployments",
        "handle_describe_deployment",
        "handle_get_services",
        "handle_get_pod_logs"
    ]
    
    for handler in handlers:
        if handler in content:
            # Find the try block in the handler function
            start_idx = content.find(f"def {handler}(")
            if start_idx == -1:
                continue
                
            try_idx = content.find("try:", start_idx)
            if try_idx == -1:
                continue
                
            # Find the line with k8s_sdk_ops
            sdk_idx = content.find("k8s_sdk_ops", try_idx)
            if sdk_idx == -1:
                continue
                
            # Find the line end
            line_end_idx = content.find("\n", sdk_idx)
            if line_end_idx == -1:
                continue
                
            # Get the line
            line = content[sdk_idx:line_end_idx]
            
            # Replace with the new SDK implementation
            new_line = line.replace("k8s_sdk_ops", "k8s_sdk_v2_ops")
            
            # Update the content
            content = content[:sdk_idx] + new_line + content[line_end_idx:]
    
    # Write the updated content
    with open(main_py, "w") as f:
        f.write(content)
    
    print("Server updated successfully")

if __name__ == "__main__":
    update_server()
