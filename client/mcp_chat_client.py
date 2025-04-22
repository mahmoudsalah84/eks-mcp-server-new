#!/usr/bin/env python3
"""
EKS MCP Chat Client - An interactive chat-like interface for the EKS MCP Server
"""

import os
import sys
import json
import cmd
import shlex
import readline
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime
import traceback

try:
    import colorama
    from colorama import Fore, Back, Style
    colorama.init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False
    class DummyColor:
        def __getattr__(self, name):
            return ""
    Fore = DummyColor()
    Back = DummyColor()
    Style = DummyColor()

class MCPChatClient(cmd.Cmd):
    """
    Interactive chat client for EKS MCP Server
    """
    
    intro = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════╗
{Fore.CYAN}║                                                          ║
{Fore.CYAN}║  {Fore.GREEN}Welcome to the EKS MCP Chat Client{Fore.CYAN}                     ║
{Fore.CYAN}║  {Fore.YELLOW}Type 'help' or '?' to list available commands{Fore.CYAN}         ║
{Fore.CYAN}║  {Fore.YELLOW}Type 'exit' or 'quit' to exit{Fore.CYAN}                         ║
{Fore.CYAN}║                                                          ║
{Fore.CYAN}╚══════════════════════════════════════════════════════════╝
{Style.RESET_ALL}"""
    
    prompt = f"{Fore.GREEN}mcp> {Style.RESET_ALL}"
    
    def __init__(self, server_url=None, api_key=None, config_file=None):
        """Initialize the chat client"""
        super().__init__()
        self.server_url = server_url
        self.api_key = api_key
        self.config_file = config_file
        self.current_region = "us-east-1"
        self.current_cluster = None
        self.history_file = os.path.expanduser("~/.mcp_chat_history")
        
        # Load configuration
        self._load_config()
        
        # Set up command history
        try:
            readline.read_history_file(self.history_file)
            readline.set_history_length(1000)
        except FileNotFoundError:
            pass
    
    def _load_config(self):
        """Load configuration from file or environment variables"""
        # Try loading from config file
        if self.config_file:
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                self.server_url = config.get('mcp_server_url', self.server_url)
                self.api_key = config.get('mcp_api_key', self.api_key)
                print(f"{Fore.GREEN}Loaded configuration from {self.config_file}{Style.RESET_ALL}")
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"{Fore.RED}Error loading config file: {e}{Style.RESET_ALL}")
        
        # If no config file or missing values, try default locations
        if not self.server_url or not self.api_key:
            default_config_paths = [
                os.path.join(os.getcwd(), 'client_config.json'),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'client_config.json'),
                os.path.expanduser('~/.eks-mcp/config.json')
            ]
            
            for path in default_config_paths:
                if os.path.exists(path):
                    try:
                        with open(path, 'r') as f:
                            config = json.load(f)
                        self.server_url = config.get('mcp_server_url', self.server_url)
                        self.api_key = config.get('mcp_api_key', self.api_key)
                        print(f"{Fore.GREEN}Loaded configuration from {path}{Style.RESET_ALL}")
                        break
                    except (json.JSONDecodeError, FileNotFoundError):
                        pass
        
        # If still no values, try environment variables
        if not self.server_url:
            self.server_url = os.environ.get('MCP_SERVER_URL')
            if self.server_url:
                print(f"{Fore.GREEN}Using MCP server URL from environment variable{Style.RESET_ALL}")
        
        if not self.api_key:
            self.api_key = os.environ.get('MCP_API_KEY')
            if self.api_key:
                print(f"{Fore.GREEN}Using MCP API key from environment variable{Style.RESET_ALL}")
        
        # Validate configuration
        if not self.server_url:
            print(f"{Fore.RED}MCP server URL not provided. Please set it using 'set server <url>'{Style.RESET_ALL}")
        
        if not self.api_key:
            print(f"{Fore.RED}MCP API key not provided. Please set it using 'set apikey <key>'{Style.RESET_ALL}")
    
    def _make_request(self, operation, parameters=None):
        """Make a request to the MCP server"""
        if parameters is None:
            parameters = {}
            
        if not self.server_url:
            return {
                'status': 'error',
                'data': None,
                'error': 'MCP server URL not set. Use "set server <url>" to set it.',
                'error_code': 'CONFIG_ERROR'
            }
        
        if not self.api_key:
            return {
                'status': 'error',
                'data': None,
                'error': 'MCP API key not set. Use "set apikey <key>" to set it.',
                'error_code': 'CONFIG_ERROR'
            }
            
        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': self.api_key
        }
        
        payload = {
            'operation': operation,
            'parameters': parameters
        }
        
        try:
            response = requests.post(
                f"{self.server_url}/mcp/v1/query",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                'status': 'error',
                'data': None,
                'error': str(e),
                'error_code': 'REQUEST_ERROR'
            }
    
    def _print_response(self, response):
        """Print the response in a formatted way"""
        if response.get('status') == 'error':
            print(f"{Fore.RED}Error: {response.get('error', 'Unknown error')}{Style.RESET_ALL}")
            if response.get('error_code'):
                print(f"{Fore.RED}Error code: {response.get('error_code')}{Style.RESET_ALL}")
            return
        
        data = response.get('data', {})
        
        if 'clusters' in data:
            print(f"{Fore.CYAN}EKS Clusters in region {self.current_region}:{Style.RESET_ALL}")
            for i, cluster in enumerate(data['clusters'], 1):
                print(f"{Fore.GREEN}{i}. {cluster}{Style.RESET_ALL}")
            print(f"\n{Fore.YELLOW}Total: {len(data['clusters'])} cluster(s){Style.RESET_ALL}")
        
        elif 'cluster' in data:
            cluster = data['cluster']
            print(f"{Fore.CYAN}Cluster Details:{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Name:      {Fore.WHITE}{cluster.get('name', 'Unknown')}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Status:    {Fore.WHITE}{cluster.get('status', 'Unknown')}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Version:   {Fore.WHITE}{cluster.get('version', 'Unknown')}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Created:   {Fore.WHITE}{cluster.get('createdAt', 'Unknown')}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Endpoint:  {Fore.WHITE}{cluster.get('endpoint', 'Unknown')}{Style.RESET_ALL}")
            
            if 'resourcesVpcConfig' in cluster:
                vpc = cluster['resourcesVpcConfig']
                print(f"\n{Fore.CYAN}VPC Configuration:{Style.RESET_ALL}")
                print(f"{Fore.GREEN}VPC ID:    {Fore.WHITE}{vpc.get('vpcId', 'Unknown')}{Style.RESET_ALL}")
                print(f"{Fore.GREEN}Subnets:   {Fore.WHITE}{', '.join(vpc.get('subnetIds', []))}{Style.RESET_ALL}")
                print(f"{Fore.GREEN}Public:    {Fore.WHITE}{vpc.get('endpointPublicAccess', False)}{Style.RESET_ALL}")
                print(f"{Fore.GREEN}Private:   {Fore.WHITE}{vpc.get('endpointPrivateAccess', False)}{Style.RESET_ALL}")
        
        elif 'namespaces' in data:
            print(f"{Fore.CYAN}Kubernetes Namespaces in cluster {self.current_cluster}:{Style.RESET_ALL}")
            for i, ns in enumerate(data['namespaces'], 1):
                print(f"{Fore.GREEN}{i}. {ns.get('name', 'Unknown')} {Fore.YELLOW}({ns.get('status', 'Unknown')}){Style.RESET_ALL}")
            print(f"\n{Fore.YELLOW}Total: {len(data['namespaces'])} namespace(s){Style.RESET_ALL}")
            
            if 'note' in data:
                print(f"\n{Fore.YELLOW}Note: {data['note']}{Style.RESET_ALL}")
        
        elif 'operations' in data:
            print(f"{Fore.CYAN}Available Operations:{Style.RESET_ALL}")
            for op in data['operations']:
                print(f"\n{Fore.GREEN}{op['name']}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}  {op.get('description', 'No description')}{Style.RESET_ALL}")
                print(f"{Fore.CYAN}  Parameters:{Style.RESET_ALL}")
                for param in op.get('parameters', []):
                    req = f"{Fore.RED}(required){Style.RESET_ALL}" if param.get('required') else f"{Fore.YELLOW}(optional){Style.RESET_ALL}"
                    default = f", default: {param.get('default')}" if 'default' in param else ""
                    print(f"    {Fore.WHITE}{param['name']}: {param.get('type', 'string')} {req}{default}{Style.RESET_ALL}")
        
        elif 'status' in data:
            print(f"{Fore.CYAN}Server Status:{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Status:    {Fore.WHITE}{data.get('status', 'Unknown')}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Version:   {Fore.WHITE}{data.get('version', 'Unknown')}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Timestamp: {Fore.WHITE}{data.get('timestamp', 'Unknown')}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Provider:  {Fore.WHITE}{data.get('provider', 'Unknown')}{Style.RESET_ALL}")
        
        else:
            print(json.dumps(data, indent=2))
    
    def emptyline(self):
        """Do nothing on empty line"""
        pass
    
    def do_exit(self, arg):
        """Exit the chat client"""
        print(f"{Fore.YELLOW}Goodbye!{Style.RESET_ALL}")
        try:
            readline.write_history_file(self.history_file)
        except Exception:
            pass
        return True
    
    def do_quit(self, arg):
        """Exit the chat client"""
        return self.do_exit(arg)
    
    def do_EOF(self, arg):
        """Exit on Ctrl+D"""
        print()  # Add a newline
        return self.do_exit(arg)
    
    def do_set(self, arg):
        """Set configuration values: set <key> <value>"""
        args = shlex.split(arg)
        if len(args) < 2:
            print(f"{Fore.RED}Usage: set <key> <value>{Style.RESET_ALL}")
            return
        
        key = args[0].lower()
        value = args[1]
        
        if key == 'server':
            self.server_url = value
            print(f"{Fore.GREEN}Server URL set to: {value}{Style.RESET_ALL}")
        elif key == 'apikey':
            self.api_key = value
            print(f"{Fore.GREEN}API key set to: {value}{Style.RESET_ALL}")
        elif key == 'region':
            self.current_region = value
            print(f"{Fore.GREEN}Current region set to: {value}{Style.RESET_ALL}")
        elif key == 'cluster':
            self.current_cluster = value
            print(f"{Fore.GREEN}Current cluster set to: {value}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Unknown configuration key: {key}{Style.RESET_ALL}")
    
    def do_get(self, arg):
        """Get current configuration values: get <key>"""
        args = shlex.split(arg)
        if not args:
            print(f"{Fore.CYAN}Current Configuration:{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Server URL:     {Fore.WHITE}{self.server_url or 'Not set'}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}API Key:        {Fore.WHITE}{'*****' if self.api_key else 'Not set'}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Current Region: {Fore.WHITE}{self.current_region}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Current Cluster: {Fore.WHITE}{self.current_cluster or 'Not set'}{Style.RESET_ALL}")
            return
        
        key = args[0].lower()
        if key == 'server':
            print(f"{Fore.GREEN}Server URL: {Fore.WHITE}{self.server_url or 'Not set'}{Style.RESET_ALL}")
        elif key == 'apikey':
            print(f"{Fore.GREEN}API Key: {Fore.WHITE}{'*****' if self.api_key else 'Not set'}{Style.RESET_ALL}")
        elif key == 'region':
            print(f"{Fore.GREEN}Current Region: {Fore.WHITE}{self.current_region}{Style.RESET_ALL}")
        elif key == 'cluster':
            print(f"{Fore.GREEN}Current Cluster: {Fore.WHITE}{self.current_cluster or 'Not set'}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Unknown configuration key: {key}{Style.RESET_ALL}")
    
    def do_health(self, arg):
        """Check the health of the MCP server"""
        try:
            response = requests.get(f"{self.server_url}/health")
            response.raise_for_status()
            self._print_response(response.json())
        except Exception as e:
            print(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")
    
    def do_operations(self, arg):
        """List available operations"""
        if not self.server_url or not self.api_key:
            print(f"{Fore.RED}Server URL and API key must be set first{Style.RESET_ALL}")
            return
        
        try:
            headers = {'X-API-Key': self.api_key}
            response = requests.get(f"{self.server_url}/mcp/v1/operations", headers=headers)
            response.raise_for_status()
            self._print_response(response.json())
        except Exception as e:
            print(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")
    
    def do_clusters(self, arg):
        """List EKS clusters in the current region"""
        args = shlex.split(arg)
        region = args[0] if args else self.current_region
        
        response = self._make_request('list_clusters', {'region': region})
        self._print_response(response)
    
    def do_describe(self, arg):
        """Describe an EKS cluster: describe <cluster_name> [region]"""
        args = shlex.split(arg)
        if not args:
            if not self.current_cluster:
                print(f"{Fore.RED}No cluster specified. Use 'describe <cluster_name>' or set a current cluster with 'set cluster <name>'{Style.RESET_ALL}")
                return
            cluster_name = self.current_cluster
        else:
            cluster_name = args[0]
            if len(args) > 1:
                region = args[1]
            else:
                region = self.current_region
        
        response = self._make_request('describe_cluster', {
            'cluster_name': cluster_name,
            'region': region
        })
        self._print_response(response)
        
        # If successful, set as current cluster
        if response.get('status') == 'success':
            self.current_cluster = cluster_name
    
    def do_namespaces(self, arg):
        """List Kubernetes namespaces: namespaces [cluster_name] [region]"""
        args = shlex.split(arg)
        
        if not args:
            if not self.current_cluster:
                print(f"{Fore.RED}No cluster specified. Use 'namespaces <cluster_name>' or set a current cluster with 'set cluster <name>'{Style.RESET_ALL}")
                return
            cluster_name = self.current_cluster
        else:
            cluster_name = args[0]
            if len(args) > 1:
                region = args[1]
            else:
                region = self.current_region
        
        response = self._make_request('list_namespaces', {
            'cluster_name': cluster_name,
            'region': region
        })
        self._print_response(response)
    
    def do_save(self, arg):
        """Save current configuration to a file: save [filename]"""
        args = shlex.split(arg)
        if args:
            filename = args[0]
        else:
            filename = os.path.join(os.getcwd(), 'client_config.json')
        
        config = {
            'mcp_server_url': self.server_url,
            'mcp_api_key': self.api_key
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"{Fore.GREEN}Configuration saved to {filename}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error saving configuration: {str(e)}{Style.RESET_ALL}")
    
    def do_load(self, arg):
        """Load configuration from a file: load <filename>"""
        args = shlex.split(arg)
        if not args:
            print(f"{Fore.RED}Usage: load <filename>{Style.RESET_ALL}")
            return
        
        filename = args[0]
        self.config_file = filename
        self._load_config()
    
    def do_clear(self, arg):
        """Clear the screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def do_time(self, arg):
        """Show current time"""
        now = datetime.now()
        print(f"{Fore.CYAN}Current time: {Fore.WHITE}{now.strftime('%Y-%m-%d %H:%M:%S')}{Style.RESET_ALL}")
    
    def default(self, line):
        """Handle unknown commands"""
        print(f"{Fore.RED}Unknown command: {line}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Type 'help' or '?' to list available commands{Style.RESET_ALL}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='EKS MCP Chat Client')
    parser.add_argument('--server', '-s', help='MCP server URL')
    parser.add_argument('--api-key', '-k', help='MCP API key')
    parser.add_argument('--config', '-c', help='Path to config file')
    
    args = parser.parse_args()
    
    try:
        client = MCPChatClient(
            server_url=args.server,
            api_key=args.api_key,
            config_file=args.config
        )
        client.cmdloop()
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {str(e)}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
