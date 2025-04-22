"""
Kubernetes operations for the EKS MCP Server
"""

import subprocess
import json
import logging
import tempfile
import os
import boto3
import base64
from typing import Dict, List, Any, Optional
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KubernetesOperations:
    """Class for Kubernetes operations"""
    
    @staticmethod
    def create_kubeconfig(cluster_name: str, region: str) -> str:
        """Create a temporary kubeconfig file for kubectl using aws eks get-token"""
        try:
            # Get cluster info
            eks_client = boto3.client('eks', region_name=region)
            cluster_info = eks_client.describe_cluster(name=cluster_name)
            cluster_endpoint = cluster_info['cluster']['endpoint']
            cluster_cert = cluster_info['cluster']['certificateAuthority']['data']
            
            # Get token using aws eks get-token
            result = subprocess.run(
                ["aws", "eks", "get-token", "--cluster-name", cluster_name, "--region", region],
                capture_output=True,
                text=True,
                check=True
            )
            token_data = json.loads(result.stdout)
            token = token_data['status']['token']
            
            # Create a temporary directory for kubeconfig
            temp_dir = tempfile.mkdtemp(prefix='kube-')
            kubeconfig_path = os.path.join(temp_dir, 'config')
            
            # Create kubeconfig content with direct token
            kubeconfig = {
                'apiVersion': 'v1',
                'kind': 'Config',
                'clusters': [{
                    'name': cluster_name,
                    'cluster': {
                        'server': cluster_endpoint,
                        'certificate-authority-data': cluster_cert
                    }
                }],
                'users': [{
                    'name': f'eks-user-{cluster_name}',
                    'user': {
                        'token': token
                    }
                }],
                'contexts': [{
                    'name': f'eks-{cluster_name}',
                    'context': {
                        'cluster': cluster_name,
                        'user': f'eks-user-{cluster_name}'
                    }
                }],
                'current-context': f'eks-{cluster_name}'
            }
            
            # Write to temporary file
            with open(kubeconfig_path, 'w') as f:
                json.dump(kubeconfig, f)
            
            logger.info(f"Created temporary kubeconfig at {kubeconfig_path}")
            return kubeconfig_path
            
        except Exception as e:
            logger.error(f"Error creating kubeconfig: {str(e)}")
            raise RuntimeError(f"Error creating kubeconfig: {str(e)}")
    
    @staticmethod
    def run_kubectl_command(command: List[str], cluster_name: str, region: str) -> Dict[str, Any]:
        """Run a kubectl command and return the result as JSON"""
        try:
            # Create temporary kubeconfig
            kubeconfig_path = KubernetesOperations.create_kubeconfig(cluster_name, region)
            
            # Add kubeconfig to command
            env = os.environ.copy()
            env['KUBECONFIG'] = kubeconfig_path
            
            # Log the command being executed
            logger.info(f"Running kubectl command: {' '.join(command)}")
            
            # Run the command
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                env=env
            )
            
            # Clean up temporary kubeconfig
            try:
                os.remove(kubeconfig_path)
                os.rmdir(os.path.dirname(kubeconfig_path))
            except Exception as e:
                logger.warning(f"Error removing temporary kubeconfig: {str(e)}")
            
            return json.loads(result.stdout)
        except subprocess.SubprocessError as e:
            logger.error(f"Error running kubectl command: {str(e)}")
            if e.stderr:
                logger.error(f"stderr: {e.stderr}")
            
            # Clean up temporary kubeconfig if it exists
            if 'kubeconfig_path' in locals():
                try:
                    os.remove(kubeconfig_path)
                    os.rmdir(os.path.dirname(kubeconfig_path))
                except Exception:
                    pass
                
            raise RuntimeError(f"Error executing kubectl command: {e.stderr if e.stderr else str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing kubectl output as JSON: {str(e)}")
            
            # Clean up temporary kubeconfig if it exists
            if 'kubeconfig_path' in locals():
                try:
                    os.remove(kubeconfig_path)
                    os.rmdir(os.path.dirname(kubeconfig_path))
                except Exception:
                    pass
                
            raise RuntimeError(f"Error parsing kubectl output as JSON: {str(e)}")
    
    @staticmethod
    def get_namespaces(cluster_name: str, region: str) -> List[Dict[str, Any]]:
        """Get all namespaces in the cluster"""
        data = KubernetesOperations.run_kubectl_command(
            ["kubectl", "get", "namespaces", "-o", "json"],
            cluster_name,
            region
        )
        namespaces = []
        
        for item in data.get("items", []):
            namespaces.append({
                "name": item.get("metadata", {}).get("name"),
                "status": item.get("status", {}).get("phase"),
                "created": item.get("metadata", {}).get("creationTimestamp")
            })
            
        logger.info(f"Found {len(namespaces)} namespaces")
        return namespaces
    
    @staticmethod
    def get_pods(cluster_name: str, namespace: str, region: str) -> List[Dict[str, Any]]:
        """Get all pods in a namespace"""
        data = KubernetesOperations.run_kubectl_command(
            ["kubectl", "get", "pods", "-n", namespace, "-o", "json"],
            cluster_name,
            region
        )
        pods = []
        
        for item in data.get("items", []):
            pod_name = item.get("metadata", {}).get("name")
            pod_status = item.get("status", {}).get("phase")
            pod_ip = item.get("status", {}).get("podIP", "N/A")
            node_name = item.get("spec", {}).get("nodeName", "N/A")
            containers = len(item.get("spec", {}).get("containers", []))
            
            pods.append({
                "name": pod_name,
                "status": pod_status,
                "node": node_name,
                "ip": pod_ip,
                "containers": containers
            })
            
        logger.info(f"Found {len(pods)} pods in namespace {namespace}")
        return pods
    
    @staticmethod
    def describe_pod(cluster_name: str, namespace: str, pod_name: str, region: str) -> Dict[str, Any]:
        """Get detailed information about a pod"""
        data = KubernetesOperations.run_kubectl_command(
            ["kubectl", "get", "pod", pod_name, "-n", namespace, "-o", "json"],
            cluster_name,
            region
        )
        
        # Extract relevant information
        metadata = data.get("metadata", {})
        spec = data.get("spec", {})
        status = data.get("status", {})
        
        pod_info = {
            "name": metadata.get("name"),
            "namespace": metadata.get("namespace"),
            "uid": metadata.get("uid"),
            "creationTimestamp": metadata.get("creationTimestamp"),
            "labels": metadata.get("labels", {}),
            "nodeName": spec.get("nodeName"),
            "hostIP": status.get("hostIP"),
            "podIP": status.get("podIP"),
            "phase": status.get("phase"),
            "containers": []
        }
        
        # Extract container information
        for container in spec.get("containers", []):
            container_info = {
                "name": container.get("name"),
                "image": container.get("image"),
                "ports": container.get("ports", []),
                "resources": container.get("resources", {})
            }
            pod_info["containers"].append(container_info)
        
        logger.info(f"Retrieved details for pod {pod_name} in namespace {namespace}")
        return pod_info
    
    @staticmethod
    def get_deployments(cluster_name: str, namespace: str, region: str) -> List[Dict[str, Any]]:
        """Get all deployments in a namespace"""
        data = KubernetesOperations.run_kubectl_command(
            ["kubectl", "get", "deployments", "-n", namespace, "-o", "json"],
            cluster_name,
            region
        )
        deployments = []
        
        for item in data.get("items", []):
            metadata = item.get("metadata", {})
            spec = item.get("spec", {})
            status = item.get("status", {})
            
            deployments.append({
                "name": metadata.get("name"),
                "namespace": metadata.get("namespace"),
                "replicas": spec.get("replicas"),
                "available": status.get("availableReplicas", 0),
                "ready": status.get("readyReplicas", 0),
                "updated": status.get("updatedReplicas", 0),
                "created": metadata.get("creationTimestamp")
            })
            
        logger.info(f"Found {len(deployments)} deployments in namespace {namespace}")
        return deployments
    
    @staticmethod
    def describe_deployment(cluster_name: str, namespace: str, deployment_name: str, region: str) -> Dict[str, Any]:
        """Get detailed information about a deployment"""
        data = KubernetesOperations.run_kubectl_command(
            ["kubectl", "get", "deployment", deployment_name, "-n", namespace, "-o", "json"],
            cluster_name,
            region
        )
        
        # Extract relevant information
        metadata = data.get("metadata", {})
        spec = data.get("spec", {})
        status = data.get("status", {})
        
        deployment_info = {
            "name": metadata.get("name"),
            "namespace": metadata.get("namespace"),
            "uid": metadata.get("uid"),
            "creationTimestamp": metadata.get("creationTimestamp"),
            "labels": metadata.get("labels", {}),
            "replicas": spec.get("replicas"),
            "strategy": spec.get("strategy", {}).get("type"),
            "selector": spec.get("selector", {}).get("matchLabels", {}),
            "status": {
                "availableReplicas": status.get("availableReplicas", 0),
                "readyReplicas": status.get("readyReplicas", 0),
                "updatedReplicas": status.get("updatedReplicas", 0),
                "conditions": status.get("conditions", [])
            },
            "containers": []
        }
        
        # Extract container information from template
        template = spec.get("template", {}).get("spec", {})
        for container in template.get("containers", []):
            container_info = {
                "name": container.get("name"),
                "image": container.get("image"),
                "ports": container.get("ports", []),
                "resources": container.get("resources", {})
            }
            deployment_info["containers"].append(container_info)
        
        logger.info(f"Retrieved details for deployment {deployment_name} in namespace {namespace}")
        return deployment_info
    
    @staticmethod
    def get_services(cluster_name: str, namespace: str, region: str) -> List[Dict[str, Any]]:
        """Get all services in a namespace"""
        data = KubernetesOperations.run_kubectl_command(
            ["kubectl", "get", "services", "-n", namespace, "-o", "json"],
            cluster_name,
            region
        )
        services = []
        
        for item in data.get("items", []):
            metadata = item.get("metadata", {})
            spec = item.get("spec", {})
            
            services.append({
                "name": metadata.get("name"),
                "namespace": metadata.get("namespace"),
                "type": spec.get("type"),
                "clusterIP": spec.get("clusterIP"),
                "externalIP": spec.get("externalIPs", ["None"])[0] if spec.get("externalIPs") else "None",
                "ports": spec.get("ports", []),
                "created": metadata.get("creationTimestamp")
            })
            
        logger.info(f"Found {len(services)} services in namespace {namespace}")
        return services
    
    @staticmethod
    def get_pod_logs(cluster_name: str, namespace: str, pod_name: str, region: str, container: Optional[str] = None, tail: int = 100) -> str:
        """Get logs from a pod"""
        command = ["kubectl", "logs", pod_name, "-n", namespace]
        
        if container:
            command.extend(["-c", container])
            
        command.extend(["--tail", str(tail)])
        
        # Create temporary kubeconfig
        kubeconfig_path = KubernetesOperations.create_kubeconfig(cluster_name, region)
        
        # Add kubeconfig to command
        env = os.environ.copy()
        env['KUBECONFIG'] = kubeconfig_path
        
        logger.info(f"Getting logs for pod {pod_name} in namespace {namespace}")
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                env=env
            )
            
            # Clean up temporary kubeconfig
            try:
                os.remove(kubeconfig_path)
                os.rmdir(os.path.dirname(kubeconfig_path))
            except Exception as e:
                logger.warning(f"Error removing temporary kubeconfig: {str(e)}")
                
            return result.stdout
        except subprocess.SubprocessError as e:
            logger.error(f"Error getting pod logs: {str(e)}")
            
            # Clean up temporary kubeconfig
            try:
                os.remove(kubeconfig_path)
                os.rmdir(os.path.dirname(kubeconfig_path))
            except Exception:
                pass
                
            raise RuntimeError(f"Error getting pod logs: {e.stderr if e.stderr else str(e)}")
