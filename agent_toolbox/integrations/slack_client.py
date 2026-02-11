"""Slack API integration client."""

import requests
import json
from typing import Dict, List, Optional, Union, Any
from ..api_client import APIClient


class SlackClient(APIClient):
    """Slack API client for sending messages and managing channels."""
    
    def __init__(self, token: str):
        """Initialize Slack client with API token."""
        super().__init__(
            base_url="https://slack.com/api",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.token = token
        
    def send_message(self, channel: str, text: str, 
                    blocks: Optional[List[Dict]] = None,
                    thread_ts: Optional[str] = None) -> Dict[str, Any]:
        """Send a message to a Slack channel."""
        data = {
            "channel": channel,
            "text": text
        }
        
        if blocks:
            data["blocks"] = blocks
            
        if thread_ts:
            data["thread_ts"] = thread_ts
            
        return self.post("chat.postMessage", json_data=data)
        
    def get_channels(self) -> List[Dict[str, Any]]:
        """Get list of channels the bot has access to."""
        response = self.get("conversations.list")
        return response.get("channels", [])
        
    def get_users(self) -> List[Dict[str, Any]]:
        """Get list of users in the workspace."""
        response = self.get("users.list")
        return response.get("members", [])
        
    def upload_file(self, file_path: str, channels: str, 
                   title: Optional[str] = None,
                   comment: Optional[str] = None) -> Dict[str, Any]:
        """Upload a file to Slack."""
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {
                'token': self.token,
                'channels': channels
            }
            
            if title:
                data['title'] = title
            if comment:
                data['initial_comment'] = comment
                
            response = requests.post(
                f"{self.base_url}/files.upload",
                data=data,
                files=files
            )
            
        return response.json()
        
    def create_channel(self, name: str, is_private: bool = False) -> Dict[str, Any]:
        """Create a new channel."""
        data = {
            "name": name,
            "is_private": is_private
        }
        return self.post("conversations.create", json_data=data)
        
    def get_channel_history(self, channel: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get message history from a channel."""
        params = {
            "channel": channel,
            "limit": limit
        }
        response = self.get("conversations.history", params=params)
        return response.get("messages", [])
        
    def react_to_message(self, channel: str, timestamp: str, emoji: str) -> Dict[str, Any]:
        """Add emoji reaction to a message."""
        data = {
            "channel": channel,
            "timestamp": timestamp,
            "name": emoji
        }
        return self.post("reactions.add", json_data=data)