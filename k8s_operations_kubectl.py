"""
Kubernetes operations using kubectl with proper authentication
"""

import os
import json
import subprocess
import logging
from typing import Dict, List, Any, Optional
from k8s_auth_config import KubernetesAuthConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KubernetesOperationsKubectl:
    """Class for Kubernetes operations using kubectl with proper authentication"""
    
    @staticmethod
    def run_kubectl_command(cluster_name: str, region: str, command: str) -> Dict[str, Any]:
        """Run a kubectl command with proper authentication"""
        try:
            # Get environment variables for kubectl
            env = KubernetesAuthConfig.setup_environment_for_kubectl(cluster_name, region)
            
            # Combine with current environment
            full_env = os.environ.copy()
            full_env.update(env)
            
            # Run kubectl command
            cmd = f"kubectl {command} -o json"
            logger.info(f"Running kubectl command: {cmd}")
            
            result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True, env=full_env)
            
            # Parse JSON output
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running kubectl command: {str(e)}")
            logger.error(f"Command output: {e.stderr}")
            raise RuntimeError(f"Error running kubectl command: {e.stderr}")
        except Exception as e:
            logger.error(f"Error in run_kubectl_command: {str(e)}")
            raise RuntimeError(f"Error in run_kubectl_command: {str(e)}")
    
    @staticmethod
    def get_namespaces(cluster_name: str, region: str) -> List[Dict[str, Any]]:
        """Get all namespaces in the cluster"""
        try:
            # Run kubectl command
            response = KubernetesOperationsKubectl.run_kubectl_command(cluster_name, region, "get namespaces")
            
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
            response = KubernetesOperationsKubectl.run_kubectl_command(cluster_name, region, f"get pods -n {namespace}")
            
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
            response = KubernetesOperationsKubectl.run_kubectl_command(cluster_name, region, f"get pod {pod_name} -n {namespace}")
            
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
            response = KubernetesOperationsKubectl.run_kubectl_command(cluster_name, region, f"get deployments -n {namespace}")
            
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
            response = KubernetesOperationsKubectl.run_kubectl_command(cluster_name, region, f"get deployment {deployment_name} -n {namespace}")
            
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
            response = KubernetesOperationsKubectl.run_kubectl_command(cluster_name, region, f"get services -n {namespace}")
            
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
        try:
            # Get environment variables for kubectl
            env = KubernetesAuthConfig.setup_environment_for_kubectl(cluster_name, region)
            
            # Combine with current environment
            full_env = os.environ.copy()
            full_env.update(env)
            
            # Build command
            cmd = f"kubectl logs {pod_name} -n {namespace}"
            if container:
                cmd += f" -c {container}"
            cmd += f" --tail={tail}"
            
            logger.info(f"Running kubectl command: {cmd}")
            
            # Run command
            result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True, env=full_env)
            
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Error getting pod logs: {str(e)}")
            logger.error(f"Command output: {e.stderr}")
            raise RuntimeError(f"Error getting pod logs: {e.stderr}")
        except Exception as e:
            logger.error(f"Error in get_pod_logs: {str(e)}")
            raise RuntimeError(f"Error in get_pod_logs: {str(e)}")
    
    @staticmethod
    def list_nodegroups(cluster_name: str, region: str) -> List[Dict[str, Any]]:
        """List all nodegroups in an EKS cluster"""
        try:
            eks_client = boto3.client('eks', region_name=region)
            response = eks_client.list_nodegroups(clusterName=cluster_name)
            
            nodegroups = []
            for nodegroup_name in response.get('nodegroups', []):
                nodegroup_info = eks_client.describe_nodegroup(
                    clusterName=cluster_name,
                    nodegroupName=nodegroup_name
                )
                
                nodegroups.append({
                    "name": nodegroup_name,
                    "status": nodegroup_info.get('nodegroup', {}).get('status'),
                    "instanceType": nodegroup_info.get('nodegroup', {}).get('instanceTypes', ['unknown'])[0],
                    "capacityType": nodegroup_info.get('nodegroup', {}).get('capacityType', 'unknown'),
                    "desiredSize": nodegroup_info.get('nodegroup', {}).get('scalingConfig', {}).get('desiredSize'),
                    "minSize": nodegroup_info.get('nodegroup', {}).get('scalingConfig', {}).get('minSize'),
                    "maxSize": nodegroup_info.get('nodegroup', {}).get('scalingConfig', {}).get('maxSize'),
                    "createdAt": nodegroup_info.get('nodegroup', {}).get('createdAt')
                })
            
            logger.info(f"Found {len(nodegroups)} nodegroups in cluster {cluster_name}")
            return nodegroups
        except Exception as e:
            logger.error(f"Error listing nodegroups: {str(e)}")
            raise RuntimeError(f"Error listing nodegroups: {str(e)}")
    
    @staticmethod
    def describe_nodegroup(cluster_name: str, nodegroup_name: str, region: str) -> Dict[str, Any]:
        """Get detailed information about a nodegroup"""
        try:
            eks_client = boto3.client('eks', region_name=region)
            response = eks_client.describe_nodegroup(
                clusterName=cluster_name,
                nodegroupName=nodegroup_name
            )
            
            nodegroup = response.get('nodegroup', {})
            
            nodegroup_info = {
                "name": nodegroup.get('nodegroupName'),
                "status": nodegroup.get('status'),
                "clusterName": nodegroup.get('clusterName'),
                "instanceType": nodegroup.get('instanceTypes', ['unknown'])[0] if nodegroup.get('instanceTypes') else 'unknown',
                "desiredSize": nodegroup.get('scalingConfig', {}).get('desiredSize'),
                "minSize": nodegroup.get('scalingConfig', {}).get('minSize'),
                "maxSize": nodegroup.get('scalingConfig', {}).get('maxSize'),
                "created": nodegroup.get('createdAt'),
                "amiType": nodegroup.get('amiType'),
                "diskSize": nodegroup.get('diskSize'),
                "subnets": nodegroup.get('subnets', []),
                "remoteAccess": nodegroup.get('remoteAccess', {}),
                "tags": nodegroup.get('tags', {}),
                "health": nodegroup.get('health', {})
            }
            
            logger.info(f"Retrieved details for nodegroup {nodegroup_name} in cluster {cluster_name}")
            return nodegroup_info
        except Exception as e:
            logger.error(f"Error describing nodegroup: {str(e)}")
            raise RuntimeError(f"Error describing nodegroup: {str(e)}")
