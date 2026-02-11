"""GitHub API integration client."""

import base64
from typing import Dict, List, Optional, Union, Any
from ..api_client import APIClient


class GitHubClient(APIClient):
    """GitHub API client for repository and issue management."""
    
    def __init__(self, token: str):
        """Initialize GitHub client with API token."""
        super().__init__(
            base_url="https://api.github.com",
            headers={"Authorization": f"token {token}"}
        )
        
    def get_repositories(self, user: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get repositories for a user (or authenticated user if None)."""
        if user:
            endpoint = f"users/{user}/repos"
        else:
            endpoint = "user/repos"
            
        return self.get(endpoint)
        
    def get_repository(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get repository information."""
        return self.get(f"repos/{owner}/{repo}")
        
    def create_repository(self, name: str, description: str = "", 
                         private: bool = False) -> Dict[str, Any]:
        """Create a new repository."""
        data = {
            "name": name,
            "description": description,
            "private": private
        }
        return self.post("user/repos", json_data=data)
        
    def get_issues(self, owner: str, repo: str, 
                  state: str = "open") -> List[Dict[str, Any]]:
        """Get issues for a repository."""
        params = {"state": state}
        return self.get(f"repos/{owner}/{repo}/issues", params=params)
        
    def create_issue(self, owner: str, repo: str, title: str,
                    body: str = "", labels: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create a new issue."""
        data = {
            "title": title,
            "body": body
        }
        
        if labels:
            data["labels"] = labels
            
        return self.post(f"repos/{owner}/{repo}/issues", json_data=data)
        
    def get_pull_requests(self, owner: str, repo: str,
                         state: str = "open") -> List[Dict[str, Any]]:
        """Get pull requests for a repository."""
        params = {"state": state}
        return self.get(f"repos/{owner}/{repo}/pulls", params=params)
        
    def create_pull_request(self, owner: str, repo: str, title: str,
                           head: str, base: str = "main",
                           body: str = "") -> Dict[str, Any]:
        """Create a new pull request."""
        data = {
            "title": title,
            "head": head,
            "base": base,
            "body": body
        }
        return self.post(f"repos/{owner}/{repo}/pulls", json_data=data)
        
    def get_file_content(self, owner: str, repo: str, path: str,
                        ref: str = "main") -> Dict[str, Any]:
        """Get file content from repository."""
        params = {"ref": ref}
        response = self.get(f"repos/{owner}/{repo}/contents/{path}", params=params)
        
        # Decode base64 content if it's a file
        if response.get("type") == "file" and "content" in response:
            content = base64.b64decode(response["content"]).decode('utf-8')
            response["decoded_content"] = content
            
        return response
        
    def update_file(self, owner: str, repo: str, path: str, content: str,
                   message: str, sha: Optional[str] = None,
                   branch: str = "main") -> Dict[str, Any]:
        """Update or create a file in repository."""
        encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        
        data = {
            "message": message,
            "content": encoded_content,
            "branch": branch
        }
        
        if sha:
            data["sha"] = sha
            
        return self.put(f"repos/{owner}/{repo}/contents/{path}", json_data=data)