#!/usr/bin/env python3
"""
EKS MCP Chat Client V6 (With Bedrock Inline Agents Support)
This script provides a conversational interface to the EKS MCP Server using Amazon Bedrock.
It supports Amazon Bedrock inline agents functionality for more efficient operation execution.
"""

import json
import argparse
import requests
import boto3
import sys
import uuid
import logging
import os
import datetime
import inspect
from typing import Dict, Any, List, Callable

# Configure logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)

timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(log_dir, f"mcp_client_{timestamp}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("mcp_client")

class MCPClient:
    """Client for interacting with the EKS MCP Server API with automatic operation discovery"""
    
    def __init__(self, server_url: str, api_key: str):
        """Initialize the MCP client with server URL and API key"""
        self.server_url = server_url
        self.api_key = api_key
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
        self.operations = {}
        self.discover_operations()
        
    def discover_operations(self):
        """Discover available operations from the MCP server"""
        logger.info(f"Discovering operations from MCP server: {self.server_url}")
        
        try:
            # Try to get operations from the server
            response = requests.get(
                f"{self.server_url}/mcp/v1/operations",
                headers=self.headers
            )
            
            if response.status_code == 200:
                operations_data = response.json()
                if operations_data.get("status") == "success":
                    operations_list = operations_data.get("data", {}).get("operations", [])
                    
                    # Convert list of operations to dictionary format
                    self.operations = {}
                    for op in operations_list:
                        op_name = op.get("name")
                        if op_name:
                            self.operations[op_name] = {
                                "description": op.get("description", "No description"),
                                "parameters": op.get("parameters", {})
                            }
                    
                    logger.info(f"Discovered {len(self.operations)} operations from server")
                    
                    # Generate dynamic methods for each operation
                    self._generate_operation_methods()
                    return
                    
            # If we get here, the discovery endpoint failed or returned unexpected data
            logger.warning(f"Failed to discover operations from server: {response.status_code}")
            logger.warning("Falling back to default operations")
            
        except Exception as e:
            logger.error(f"Error discovering operations: {str(e)}")
            logger.warning("Falling back to default operations")
            
        # Fall back to default operations if discovery fails
        self._setup_default_operations()
    
    def _setup_default_operations(self):
        """Set up default operations if discovery fails"""
        self.operations = {
            "list_clusters": {
                "description": "List EKS clusters in the specified region",
                "parameters": {"region": "AWS region (e.g., us-east-1)"}
            },
            "describe_cluster": {
                "description": "Get detailed information about an EKS cluster",
                "parameters": {
                    "cluster_name": "Name of the EKS cluster",
                    "region": "AWS region (e.g., us-east-1)"
                }
            },
            "list_nodegroups": {
                "description": "List nodegroups for an EKS cluster",
                "parameters": {
                    "cluster_name": "Name of the EKS cluster",
                    "region": "AWS region (e.g., us-east-1)"
                }
            },
            "describe_nodegroup": {
                "description": "Get detailed information about a nodegroup",
                "parameters": {
                    "cluster_name": "Name of the EKS cluster",
                    "nodegroup_name": "Name of the nodegroup",
                    "region": "AWS region (e.g., us-east-1)"
                }
            },
            "list_namespaces": {
                "description": "List Kubernetes namespaces in the cluster",
                "parameters": {
                    "cluster_name": "Name of the EKS cluster",
                    "region": "AWS region (e.g., us-east-1)"
                }
            },
            "list_pods": {
                "description": "List pods in a namespace",
                "parameters": {
                    "cluster_name": "Name of the EKS cluster",
                    "namespace": "Kubernetes namespace",
                    "region": "AWS region (e.g., us-east-1)"
                }
            }
        }
        
        # Generate methods for default operations
        self._generate_operation_methods()
        
    def _generate_operation_methods(self):
        """Dynamically generate methods for each operation"""
        for op_name, op_info in self.operations.items():
            # Create a method name that's valid Python
            method_name = op_name.replace('-', '_')
            
            # Get the parameters for this operation
            params_dict = op_info.get("parameters", {})
            params = list(params_dict.keys()) if isinstance(params_dict, dict) else []
            
            # Create a dynamic method for this operation
            def create_method(operation, required_params):
                def method(**kwargs):
                    # Check that all required parameters are provided
                    for param in required_params:
                        if param not in kwargs:
                            raise ValueError(f"Missing required parameter: {param}")
                    
                    # Call the operation
                    return self.query(operation, kwargs)
                
                # Set the method's docstring
                method.__doc__ = f"{op_info.get('description', 'No description')}\nParameters: {', '.join(required_params)}"
                return method
            
            # Add the method to the class instance
            setattr(self, method_name, create_method(op_name, params))
            
            logger.debug(f"Generated method for operation: {op_name}")
    
    def query(self, operation: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Send a query to the MCP server"""
        payload = {
            "operation": operation,
            "parameters": parameters
        }
        
        logger.info(f"MCP Server Request - Operation: {operation}, Parameters: {json.dumps(parameters)}")
        
        try:
            response = requests.post(
                f"{self.server_url}/mcp/v1/query",
                headers=self.headers,
                json=payload
            )
            
            response_data = response.json()
            
            # Log response status
            status = response_data.get("status", "unknown")
            logger.info(f"MCP Server Response - Status: {status}, Operation: {operation}")
            
            # Log detailed response for debugging (excluding large data payloads)
            if status != "success":
                logger.error(f"MCP Server Error - Operation: {operation}, Response: {json.dumps(response_data)}")
            
            return response_data
            
        except Exception as e:
            logger.error(f"MCP Server Request Failed - Operation: {operation}, Error: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def list_available_operations(self) -> List[str]:
        """Return a list of available operations"""
        return list(self.operations.keys())
    
    def get_operation_info(self, operation: str) -> Dict[str, Any]:
        """Get information about a specific operation"""
        return self.operations.get(operation, {})
    
    def execute_operation(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Execute an operation by name with the given parameters"""
        if operation not in self.operations:
            return {"status": "error", "message": f"Unknown operation: {operation}"}
            
        # Get the required parameters for this operation
        required_params = self.operations[operation].get("parameters", [])
        
        # Check that all required parameters are provided
        for param in required_params:
            if param not in kwargs:
                return {"status": "error", "message": f"Missing required parameter: {param}"}
        
        # Call the operation
        return self.query(operation, kwargs)

class BedrockChat:
    """Class for interacting with Amazon Bedrock for conversational AI with inline agents support"""
    
    def __init__(self, region: str = "us-east-1", model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"):
        """Initialize the Bedrock client"""
        self.bedrock_runtime = boto3.client('bedrock-runtime', region_name=region)
        self.model_id = model_id
        self.session_id = str(uuid.uuid4())
        self.verbose = False
        
    def chat(self, prompt: str, system_instruction: str = None, enable_inline_agents: bool = True) -> str:
        """Generate a response using the Bedrock model with inline agents support"""
        try:
            # For Claude models with inline agents
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1024,
                "temperature": 0.7,
                "system": system_instruction if system_instruction else "",
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }
            
            # Add inline agents configuration if enabled
            if enable_inline_agents and "claude-3" in self.model_id:
                request_body["tools"] = [{
                    "name": "mcp_operation",
                    "description": "Execute an operation on the EKS MCP server",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "description": "The name of the operation to execute"
                            },
                            "parameters": {
                                "type": "object",
                                "description": "Parameters for the operation"
                            }
                        },
                        "required": ["operation"]
                    }
                }]
                
                # Enable tool use in the request with proper format
                request_body["tool_choice"] = {"type": "auto"}
            
            logger.info(f"Bedrock Request - Model: {self.model_id}, Prompt Length: {len(prompt)}")
            if self.verbose:
                print(f"\nSending request to Bedrock model: {self.model_id}")
                print(f"Request body: {json.dumps(request_body, indent=2)}")
            
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response.get('body').read())
            if self.verbose:
                print(f"\nReceived response from Bedrock:")
                print(f"Response body: {json.dumps(response_body, indent=2)}")
            
            # Handle tool use in response if present
            if any(item.get("type") == "tool_use" for item in response_body.get("content", [])):
                logger.info("Tool use detected in response")
                if self.verbose:
                    print("\nTool use detected in response")
                
                # Find the tool use item
                for item in response_body.get("content", []):
                    if item.get("type") == "tool_use":
                        tool_id = item.get("id")
                        tool_name = item.get("name")
                        tool_input = item.get("input", {})
                        
                        if tool_name == "mcp_operation":
                            operation = tool_input.get("operation")
                            parameters = tool_input.get("parameters", {})
                            
                            if self.verbose:
                                print(f"\nExecuting MCP operation: {operation}")
                                print(f"Parameters: {json.dumps(parameters, indent=2)}")
                                
                            logger.info(f"Executing MCP operation: {operation}")
                            operation_result = self._execute_mcp_operation(operation, parameters)
                            
                            # Send the tool output back to the model
                            return self._continue_with_tool_output(prompt, system_instruction, tool_id, operation_result)
            
            # Regular response without tool use
            if "content" in response_body:
                content_items = response_body.get("content", [])
                response_text = ""
                for item in content_items:
                    if item.get("type") == "text":
                        response_text += item.get("text", "")
                
                logger.info(f"Bedrock Response - Model: {self.model_id}, Response Length: {len(response_text)}")
                return response_text
            else:
                error_msg = "No content found in response"
                logger.error(error_msg)
                if self.verbose:
                    print(f"\nError: {error_msg}")
                return f"Error: {error_msg}"
                
        except Exception as e:
            logger.error(f"Bedrock Request Failed - Model: {self.model_id}, Error: {str(e)}")
            return f"Error generating response: {str(e)}"
    
    def _execute_mcp_operation(self, operation: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an MCP operation and return the result"""
        # This is a placeholder - the actual implementation will use the MCPClient
        # We'll connect this to the MCPClient instance in the main function
        logger.warning("MCP operation execution not implemented yet")
        return {"status": "error", "message": "MCP operation execution not implemented yet"}
    
    def _continue_with_tool_output(self, original_prompt: str, system_instruction: str, 
                                  tool_id: str, tool_output: Dict[str, Any]) -> str:
        """Continue the conversation with the tool output"""
        try:
            # Format the tool output as JSON string
            tool_output_str = json.dumps(tool_output)
            
            if self.verbose:
                print(f"\nContinuing conversation with tool output:")
                print(f"Tool ID: {tool_id}")
                print(f"Tool output: {tool_output_str}")
            
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1024,
                "temperature": 0.7,
                "system": system_instruction if system_instruction else "",
                "messages": [
                    {"role": "user", "content": original_prompt},
                    {"role": "assistant", "content": [
                        {
                            "type": "tool_use",
                            "id": tool_id,
                            "name": "mcp_operation",
                            "input": {
                                "operation": "placeholder",
                                "parameters": {}
                            }
                        }
                    ]},
                    {"role": "user", "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": tool_output_str
                        }
                    ]}
                ],
                # Include tools definition in the follow-up request
                "tools": [{
                    "name": "mcp_operation",
                    "description": "Execute an operation on the EKS MCP server",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "description": "The name of the operation to execute"
                            },
                            "parameters": {
                                "type": "object",
                                "description": "Parameters for the operation"
                            }
                        },
                        "required": ["operation"]
                    }
                }],
                # Enable tool choice in the follow-up request
                "tool_choice": {"type": "auto"}
            }
            
            logger.info("Continuing conversation with tool output")
            
            if self.verbose:
                print(f"\nSending follow-up request to Bedrock:")
                print(f"Request body: {json.dumps(request_body, indent=2)}")
            
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response.get('body').read())
            
            if self.verbose:
                print(f"\nReceived follow-up response from Bedrock:")
                print(f"Response body: {json.dumps(response_body, indent=2)}")
            
            # Extract text from content
            content_items = response_body.get('content', [])
            response_text = ""
            for item in content_items:
                if item.get("type") == "text":
                    response_text += item.get("text", "")
            
            logger.info(f"Bedrock Response with tool output - Response Length: {len(response_text)}")
            
            return response_text
                
        except Exception as e:
            logger.error(f"Bedrock Request Failed - Error: {str(e)}")
            return f"Error generating response with tool output: {str(e)}"

class BedrockInlineAgent:
    """Class to handle Bedrock inline agents integration with MCP operations"""
    
    def __init__(self, mcp_client: MCPClient, bedrock_chat: BedrockChat):
        """Initialize the inline agent with MCP client and Bedrock chat"""
        self.mcp_client = mcp_client
        self.bedrock_chat = bedrock_chat
        
        # Connect the MCP client to the Bedrock chat
        self.bedrock_chat._execute_mcp_operation = self._execute_mcp_operation
        
    def _execute_mcp_operation(self, operation: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an MCP operation using the MCP client"""
        logger.info(f"Executing MCP operation via inline agent: {operation}")
        
        try:
            # Check if the operation exists
            if operation not in self.mcp_client.operations:
                error_msg = f"Unknown operation: {operation}"
                logger.error(error_msg)
                return {"status": "error", "message": error_msg}
            
            # Execute the operation
            result = self.mcp_client.execute_operation(operation, **parameters)
            logger.info(f"MCP operation result status: {result.get('status', 'unknown')}")
            return result
            
        except Exception as e:
            error_msg = f"Error executing MCP operation: {str(e)}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}
    
    def chat(self, prompt: str, system_instruction: str = None) -> str:
        """Generate a response using the Bedrock model with inline agents support"""
        return self.bedrock_chat.chat(prompt, system_instruction, enable_inline_agents=True)

def gather_cluster_info(mcp_client: MCPClient, region: str) -> str:
    """Gather information about EKS clusters and format it as instructions"""
    logger.info(f"Gathering cluster information for region: {region}")
    
    instructions = """
You are an EKS MCP Assistant, an AI that helps users interact with their Amazon EKS clusters.
MCP stands for Model Context Protocol, which provides context about EKS clusters to AI models.
You have access to information about the user's EKS clusters and can answer questions about them.

IMPORTANT INSTRUCTIONS:
1. When the user asks for information that can be retrieved using an available MCP operation, 
   ALWAYS use the MCP operation directly using the mcp_operation tool.
2. Be concise and direct in your responses.
3. Provide specific information about their EKS clusters when relevant.
4. Format technical information in a readable way using markdown.
5. If you don't know something, say so rather than making up information.

EXAMPLES OF WHEN TO USE MCP OPERATIONS:
- If the user asks "What clusters do I have?" → Use the list_clusters operation
- If the user asks "Tell me about my cluster X" → Use the describe_cluster operation
- If the user asks "What namespaces are in my cluster?" → Use the list_namespaces operation
- If the user asks "Can you show me my EKS resources?" → Use list_clusters followed by describe_cluster
- If the user asks "What's running in my Kubernetes cluster?" → Use list_namespaces on their cluster

ALWAYS PREFER using MCP operations over suggesting AWS CLI or kubectl commands when the information
can be retrieved through the MCP server.

Here's what you know about the user's EKS environment:
"""
    
    # Add information about available operations
    operations = mcp_client.list_available_operations()
    instructions += f"\nAvailable MCP operations: {', '.join(operations)}\n"
    
    # Add detailed information about each operation
    instructions += "\nOperation details:\n"
    for op in operations:
        op_info = mcp_client.get_operation_info(op)
        params = op_info.get("parameters", [])
        desc = op_info.get("description", "No description")
        instructions += f"- {op}: {desc}\n"
        instructions += f"  Parameters: {', '.join(params)}\n"
    
    # Get cluster information
    try:
        clusters_response = mcp_client.execute_operation("list_clusters", region=region)
        if clusters_response.get("status") != "success":
            error_msg = f"Unable to retrieve cluster information: {clusters_response.get('message', 'Unknown error')}"
            logger.error(error_msg)
            instructions += f"\n{error_msg}"
            return instructions
            
        clusters = clusters_response.get("data", {}).get("clusters", [])
        if not clusters:
            logger.info("No EKS clusters found in the account")
            instructions += "\nNo EKS clusters found in the account."
            return instructions
            
        logger.info(f"Found {len(clusters)} EKS clusters")
        
        # Add information about each cluster
        for cluster in clusters:
            # Extract the cluster name from the cluster object
            if isinstance(cluster, dict):
                cluster_name = cluster.get("name")
            else:
                cluster_name = cluster  # If it's already a string
                
            if not cluster_name:
                logger.warning("Skipping cluster with no name")
                continue
                
            instructions += f"\n## Cluster: {cluster_name}\n"
            logger.info(f"Getting details for cluster: {cluster_name}")
            
            # Get detailed cluster information
            details = mcp_client.execute_operation("describe_cluster", cluster_name=cluster_name, region=region)
            if details.get("status") != "success":
                error_msg = f"Unable to retrieve details for cluster {cluster_name}"
                logger.error(error_msg)
                instructions += f"{error_msg}\n"
                continue
                
            cluster = details.get("data", {}).get("cluster", {})
            if not cluster:
                logger.warning(f"Empty cluster data for {cluster_name}")
                continue
                
            # Add cluster details
            instructions += f"- Status: {cluster.get('status')}\n"
            instructions += f"- Version: {cluster.get('version')}\n"
            instructions += f"- Region: {region}\n"
            instructions += f"- Created: {cluster.get('createdAt')}\n"
            
            # Add VPC configuration
            vpc_config = cluster.get('resourcesVpcConfig', {})
            if vpc_config:
                instructions += f"- VPC ID: {vpc_config.get('vpcId')}\n"
                instructions += f"- Public Access: {vpc_config.get('endpointPublicAccess')}\n"
                instructions += f"- Private Access: {vpc_config.get('endpointPrivateAccess')}\n"
            
            # Add nodegroup information if available
            if "list_nodegroups" in operations:
                try:
                    nodegroups_response = mcp_client.execute_operation("list_nodegroups", 
                                                                     cluster_name=cluster_name, 
                                                                     region=region)
                    if nodegroups_response.get("status") == "success":
                        nodegroups = nodegroups_response.get("data", {}).get("nodegroups", [])
                        if nodegroups:
                            instructions += "\n### Nodegroups:\n"
                            for nodegroup in nodegroups:
                                # Extract nodegroup name
                                if isinstance(nodegroup, dict):
                                    ng_name = nodegroup.get("name")
                                else:
                                    ng_name = nodegroup  # If it's already a string
                                    
                                if ng_name:
                                    instructions += f"- {ng_name}\n"
                except Exception as e:
                    logger.error(f"Error getting nodegroups for cluster {cluster_name}: {str(e)}")
            
            # Get namespaces for this cluster
            try:
                namespaces_response = mcp_client.execute_operation("list_namespaces", 
                                                                 cluster_name=cluster_name, 
                                                                 region=region)
                if namespaces_response.get("status") == "success":
                    namespaces = namespaces_response.get("data", {}).get("namespaces", [])
                    if namespaces:
                        instructions += "\n### Namespaces:\n"
                        for ns in namespaces:
                            ns_name = ns.get("name", "unknown")
                            ns_status = ns.get("status", "unknown")
                            instructions += f"- {ns_name} ({ns_status})\n"
            except Exception as e:
                logger.error(f"Error getting namespaces for cluster {cluster_name}: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error gathering cluster information: {str(e)}")
        instructions += f"\nError gathering cluster information: {str(e)}"
    
    # Add final reminder about using MCP operations
    instructions += """
\nREMINDER: Always use the available MCP operations to retrieve information about the user's EKS clusters.
When the user asks for information that can be obtained through an MCP operation, use the mcp_operation tool
rather than suggesting AWS CLI commands or kubectl commands.

HOW TO USE THE MCP_OPERATION TOOL:
When you need to execute an MCP operation, use the mcp_operation tool with the following format:
{
  "operation": "operation_name",
  "parameters": {
    "param1": "value1",
    "param2": "value2"
  }
}

For example, to list clusters in us-east-1:
{
  "operation": "list_clusters",
  "parameters": {
    "region": "us-east-1"
  }
}
"""
    
    logger.info("Finished gathering cluster information")
    return instructions
class ConversationTracker:
    """Class to track conversation context without using the API's conversation history"""
    
    def __init__(self, max_history: int = 5):
        self.history = []
        self.max_history = max_history
        
    def add_exchange(self, user_input: str, assistant_response: str):
        """Add a user-assistant exchange to the history"""
        self.history.append((user_input, assistant_response))
        
        # Keep history manageable
        if len(self.history) > self.max_history:
            self.history.pop(0)
            
    def get_context_prompt(self) -> str:
        """Generate a prompt that includes conversation context"""
        if not self.history:
            return ""
            
        context = "Here's our conversation so far:\n\n"
        for i, (user, assistant) in enumerate(self.history):
            context += f"User: {user}\n"
            context += f"Assistant: {assistant}\n\n"
            
        context += "Please keep this conversation context in mind when responding to my next question."
        return context

def load_config(config_file=None):
    """Load configuration from a file"""
    server_url = None
    api_key = None
    
    # List of possible config file locations in order of preference
    config_files = [
        config_file,  # User-specified config file
        os.path.join(os.getcwd(), 'client_config.json'),  # Current directory
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'client_config.json'),  # Same directory
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'client_config.json'),  # Parent directory
        os.path.expanduser('~/.eks-mcp/config.json')  # User's home directory
    ]
    
    # Try each config file location
    for file_path in config_files:
        if file_path and os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    config = json.load(f)
                    server_url = config.get('mcp_server_url')
                    api_key = config.get('mcp_api_key')
                    logger.info(f"Loaded configuration from {file_path}")
                    break
            except (json.JSONDecodeError, FileNotFoundError) as e:
                logger.warning(f"Error loading config file {file_path}: {e}")
    
    # Fall back to environment variables if config file not found or incomplete
    if not server_url:
        server_url = os.environ.get('MCP_SERVER_URL')
        if server_url:
            logger.info("Using MCP server URL from environment variable")
    
    if not api_key:
        api_key = os.environ.get('MCP_API_KEY')
        if api_key:
            logger.info("Using MCP API key from environment variable")
    
    return server_url, api_key

def main():
    parser = argparse.ArgumentParser(description='EKS MCP Chat Client V6 with Bedrock Inline Agents')
    parser.add_argument('--server-url', type=str, 
                        help='MCP server URL (overrides config file)')
    parser.add_argument('--api-key', type=str,
                        help='API key for authentication (overrides config file)')
    parser.add_argument('--config', type=str,
                        help='Path to config file')
    parser.add_argument('--region', type=str, default='us-east-1',
                        help='AWS region')
    parser.add_argument('--model', type=str, default='anthropic.claude-3-sonnet-20240229-v1:0',
                        help='Bedrock model ID')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')
    parser.add_argument('--list-operations', action='store_true',
                        help='List available MCP operations and exit')
    parser.add_argument('--disable-inline-agents', action='store_true',
                        help='Disable Bedrock inline agents functionality')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose output of API requests and responses')
    
    args = parser.parse_args()
    
    # Load configuration from file if not provided via command line
    config_server_url, config_api_key = load_config(args.config)
    
    # Command line args take precedence over config file
    server_url = args.server_url or config_server_url
    api_key = args.api_key or config_api_key
    
    # Check if we have the required configuration
    if not server_url:
        logger.error("MCP server URL not provided. Please specify via --server-url, config file, or MCP_SERVER_URL environment variable.")
        sys.exit(1)
    
    if not api_key:
        logger.error("MCP API key not provided. Please specify via --api-key, config file, or MCP_API_KEY environment variable.")
        sys.exit(1)
    
    # Set debug logging if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
        
    # Set verbose output if requested
    verbose = args.verbose
    
    logger.info(f"Starting MCP Chat Client V6 - Server: {server_url}, Region: {args.region}, Model: {args.model}")
    
    # Initialize the MCP client
    mcp_client = MCPClient(server_url, api_key)
    
    # If --list-operations flag is provided, list operations and exit
    if args.list_operations:
        operations = mcp_client.list_available_operations()
        print(f"Available MCP operations ({len(operations)}):")
        for op in operations:
            op_info = mcp_client.get_operation_info(op)
            params = op_info.get("parameters", [])
            desc = op_info.get("description", "No description")
            print(f"  - {op}: {desc}")
            print(f"    Parameters: {', '.join(params)}")
        return
    
    # Initialize the Bedrock chat
    bedrock_chat = BedrockChat(region=args.region, model_id=args.model)
    
    # Pass verbose flag to the chat interface
    bedrock_chat.verbose = args.verbose
    
    # Initialize the inline agent if enabled
    if not args.disable_inline_agents:
        logger.info("Initializing Bedrock inline agent")
        inline_agent = BedrockInlineAgent(mcp_client, bedrock_chat)
        chat_interface = inline_agent
    else:
        logger.info("Bedrock inline agents disabled")
        chat_interface = bedrock_chat
    
    # Initialize conversation tracker
    conversation = ConversationTracker()
    
    print("Gathering information about your EKS clusters...")
    instructions = gather_cluster_info(mcp_client, args.region)
    
    # Start conversation
    print("\nEKS MCP Chat Assistant V6 with Bedrock Inline Agents")
    print(f"Log file: {log_file}")
    print("Type 'exit' or 'quit' to end the conversation")
    print("Type 'operations' to list available MCP operations")
    print("Type 'verbose' to toggle verbose output")
    print("-" * 50)
    
    while True:
        user_input = input("\nYou: ")
        
        if user_input.lower() in ['exit', 'quit']:
            logger.info("User ended conversation")
            print("Goodbye!")
            break
            
        # Special command to list operations
        if user_input.lower() == 'operations':
            operations = mcp_client.list_available_operations()
            print(f"\nAvailable MCP operations ({len(operations)}):")
            for op in operations:
                op_info = mcp_client.get_operation_info(op)
                params = op_info.get("parameters", [])
                desc = op_info.get("description", "No description")
                print(f"  - {op}: {desc}")
                print(f"    Parameters: {', '.join(params)}")
            continue
            
        # Special command to toggle verbose output
        if user_input.lower() == 'verbose':
            chat_interface.verbose = not chat_interface.verbose
            print(f"\nVerbose output {'enabled' if chat_interface.verbose else 'disabled'}")
            continue
            
        logger.info(f"User input: {user_input}")
        
        # Get conversation context
        context_prompt = conversation.get_context_prompt()
        
        # Combine context with current query if we have history
        full_prompt = user_input
        if context_prompt:
            full_prompt = f"{context_prompt}\n\nNew question: {user_input}"
            logger.debug(f"Full prompt with context: {full_prompt}")
            
        # Generate response with a fresh API call each time
        response = chat_interface.chat(full_prompt, instructions)
        
        # Update conversation tracker
        conversation.add_exchange(user_input, response)
        
        print("\nAssistant:", response)

if __name__ == "__main__":
    main()
