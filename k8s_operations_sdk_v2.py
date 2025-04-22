"""
Kubernetes operations for the EKS MCP Server using AWS SDK - Version 2
"""

import logging
import boto3
import base64
import json
import requests
import tempfile
import os
import subprocess
from typing import Dict, List, Any, Optional
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KubernetesOperationsSDKV2:
    """Class for Kubernetes operations using AWS SDK"""
    
    @staticmethod
    def get_eks_token(cluster_name: str, region: str) -> str:
        """Get a token for EKS authentication using AWS CLI"""
        try:
            # Use AWS CLI to get the token
            cmd = f"aws eks get-token --cluster-name {cluster_name} --region {region}"
            result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
            token_data = json.loads(result.stdout)
            return token_data['status']['token']
        except Exception as e:
            logger.error(f"Error getting EKS token via CLI: {str(e)}")
            raise RuntimeError(f"Error getting EKS token: {str(e)}")
    
    @staticmethod
    def create_kubeconfig(cluster_name: str, region: str) -> str:
        """Create a kubeconfig file for the EKS cluster"""
        try:
            # Get EKS client
            eks_client = boto3.client('eks', region_name=region)
            
            # Get cluster info
            response = eks_client.describe_cluster(name=cluster_name)
            endpoint = response['cluster']['endpoint']
            ca_data = response['cluster']['certificateAuthority']['data']
            
            # Get token
            token = KubernetesOperationsSDKV2.get_eks_token(cluster_name, region)
            
            # Create kubeconfig
            kubeconfig = {
                "apiVersion": "v1",
                "kind": "Config",
                "clusters": [
                    {
                        "cluster": {
                            "server": endpoint,
                            "certificate-authority-data": ca_data
                        },
                        "name": cluster_name
                    }
                ],
                "contexts": [
                    {
                        "context": {
                            "cluster": cluster_name,
                            "user": "aws"
                        },
                        "name": cluster_name
                    }
                ],
                "current-context": cluster_name,
                "preferences": {},
                "users": [
                    {
                        "name": "aws",
                        "user": {
                            "token": token
                        }
                    }
                ]
            }
            
            # Write kubeconfig to temp file
            fd, kubeconfig_path = tempfile.mkstemp(prefix='kubeconfig-', suffix='.json')
            with os.fdopen(fd, 'w') as f:
                json.dump(kubeconfig, f)
            
            return kubeconfig_path
        except Exception as e:
            logger.error(f"Error creating kubeconfig: {str(e)}")
            raise RuntimeError(f"Error creating kubeconfig: {str(e)}")
    
    @staticmethod
    def run_kubectl_command(cluster_name: str, region: str, command: str) -> Dict[str, Any]:
        """Run a kubectl command using the kubeconfig file"""
        kubeconfig_path = None
        try:
            # Create kubeconfig
            kubeconfig_path = KubernetesOperationsSDKV2.create_kubeconfig(cluster_name, region)
            
            # Run kubectl command
            cmd = f"KUBECONFIG={kubeconfig_path} kubectl {command} -o json"
            logger.info(f"Running kubectl command: {cmd}")
            
            result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
            
            # Parse JSON output
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running kubectl command: {str(e)}")
            logger.error(f"Command output: {e.stderr}")
            raise RuntimeError(f"Error running kubectl command: {e.stderr}")
        except Exception as e:
            logger.error(f"Error in run_kubectl_command: {str(e)}")
            raise RuntimeError(f"Error in run_kubectl_command: {str(e)}")
        finally:
            # Clean up
            if kubeconfig_path and os.path.exists(kubeconfig_path):
                os.remove(kubeconfig_path)
    
    @staticmethod
    def get_namespaces(cluster_name: str, region: str) -> List[Dict[str, Any]]:
        """Get all namespaces in the cluster"""
        try:
            # Run kubectl command
            response = KubernetesOperationsSDKV2.run_kubectl_command(cluster_name, region, "get namespaces")
            
            namespaces = []
            for item in response.get("items", []):
                namespaces.append({
                    "name": item.get("metadata", {}).get("name"),
                    "status": item.get("status", {}).get("phase"),
                    "created": item.get("metadata", {}).get("creationTimestamp")
                })
                
            logger.info(f"Found {len(namespaces)} namespaces")
            return namespaces
        except Exception as e:
            logger.error(f"Error getting namespaces: {str(e)}")
            raise RuntimeError(f"Error getting namespaces: {str(e)}")
    
    @staticmethod
    def get_pods(cluster_name: str, namespace: str, region: str) -> List[Dict[str, Any]]:
        """Get all pods in a namespace"""
        try:
            # Run kubectl command
            response = KubernetesOperationsSDKV2.run_kubectl_command(cluster_name, region, f"get pods -n {namespace}")
            
            pods = []
            for item in response.get("items", []):
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
        except Exception as e:
            logger.error(f"Error getting pods: {str(e)}")
            raise RuntimeError(f"Error getting pods: {str(e)}")
    
    @staticmethod
    def describe_pod(cluster_name: str, namespace: str, pod_name: str, region: str) -> Dict[str, Any]:
        """Get detailed information about a pod"""
        try:
            # Run kubectl command
            response = KubernetesOperationsSDKV2.run_kubectl_command(cluster_name, region, f"get pod {pod_name} -n {namespace}")
            
            # Extract relevant information
            metadata = response.get("metadata", {})
            spec = response.get("spec", {})
            status = response.get("status", {})
            
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
        except Exception as e:
            logger.error(f"Error describing pod: {str(e)}")
            raise RuntimeError(f"Error describing pod: {str(e)}")
    
    @staticmethod
    def get_deployments(cluster_name: str, namespace: str, region: str) -> List[Dict[str, Any]]:
        """Get all deployments in a namespace"""
        try:
            # Run kubectl command
            response = KubernetesOperationsSDKV2.run_kubectl_command(cluster_name, region, f"get deployments -n {namespace}")
            
            deployments = []
            for item in response.get("items", []):
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
        except Exception as e:
            logger.error(f"Error getting deployments: {str(e)}")
            raise RuntimeError(f"Error getting deployments: {str(e)}")
    
    @staticmethod
    def describe_deployment(cluster_name: str, namespace: str, deployment_name: str, region: str) -> Dict[str, Any]:
        """Get detailed information about a deployment"""
        try:
            # Run kubectl command
            response = KubernetesOperationsSDKV2.run_kubectl_command(cluster_name, region, f"get deployment {deployment_name} -n {namespace}")
            
            # Extract relevant information
            metadata = response.get("metadata", {})
            spec = response.get("spec", {})
            status = response.get("status", {})
            
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
        except Exception as e:
            logger.error(f"Error describing deployment: {str(e)}")
            raise RuntimeError(f"Error describing deployment: {str(e)}")
    
    @staticmethod
    def get_services(cluster_name: str, namespace: str, region: str) -> List[Dict[str, Any]]:
        """Get all services in a namespace"""
        try:
            # Run kubectl command
            response = KubernetesOperationsSDKV2.run_kubectl_command(cluster_name, region, f"get services -n {namespace}")
            
            services = []
            for item in response.get("items", []):
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
        except Exception as e:
            logger.error(f"Error getting services: {str(e)}")
            raise RuntimeError(f"Error getting services: {str(e)}")
    
    @staticmethod
    def get_pod_logs(cluster_name: str, namespace: str, pod_name: str, region: str, container: Optional[str] = None, tail: int = 100) -> str:
        """Get logs from a pod"""
        kubeconfig_path = None
        try:
            # Create kubeconfig
            kubeconfig_path = KubernetesOperationsSDKV2.create_kubeconfig(cluster_name, region)
            
            # Build command
            cmd = f"KUBECONFIG={kubeconfig_path} kubectl logs {pod_name} -n {namespace}"
            if container:
                cmd += f" -c {container}"
            cmd += f" --tail={tail}"
            
            logger.info(f"Running kubectl command: {cmd}")
            
            # Run command
            result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
            
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Error getting pod logs: {str(e)}")
            logger.error(f"Command output: {e.stderr}")
            raise RuntimeError(f"Error getting pod logs: {e.stderr}")
        except Exception as e:
            logger.error(f"Error in get_pod_logs: {str(e)}")
            raise RuntimeError(f"Error in get_pod_logs: {str(e)}")
        finally:
            # Clean up
            if kubeconfig_path and os.path.exists(kubeconfig_path):
                os.remove(kubeconfig_path)
