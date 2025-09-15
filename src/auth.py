"""B2 authentication using 1Password CLI."""

import json
import subprocess
from typing import Dict, Optional
from pathlib import Path
from loguru import logger

from .config import Config


class B2AuthError(Exception):
    """Custom exception for B2 authentication errors."""
    pass


class B2Auth:
    """Handles B2 authentication using 1Password CLI."""
    
    def __init__(self, config: Config):
        """Initialize with configuration."""
        self.config = config
        self.credentials: Optional[Dict[str, str]] = None
    
    def check_1password_session(self) -> bool:
        """Check if 1Password CLI session is active."""
        try:
            result = subprocess.run(
                [Config.OP_CLI, "account", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def get_1password_credentials(self) -> Dict[str, str]:
        """Retrieve B2 credentials from 1Password."""
        if not self.check_1password_session():
            logger.error("1Password CLI session not active. Please run 'op signin' first.")
            raise B2AuthError("1Password session required")
        
        try:
            # Get the item details from 1Password
            result = subprocess.run(
                [
                    Config.OP_CLI, "item", "get", self.config.op_item_name,
                    "--format", "json"
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to retrieve item '{self.config.op_item_name}' from 1Password")
                logger.error(f"Error: {result.stderr}")
                raise B2AuthError(f"1Password item '{self.config.op_item_name}' not found")
            
            item_data = json.loads(result.stdout)
            
            # Extract credentials from the item
            credentials = {}
            for field in item_data.get('fields', []):
                if field.get('label') in ['keyID', 'keyName', 'Bucket', 'applicationKey']:
                    credentials[field['label']] = field.get('value', '')
            
            # Validate required fields
            required_fields = ['keyID', 'applicationKey']
            missing_fields = [field for field in required_fields if not credentials.get(field)]
            
            if missing_fields:
                raise B2AuthError(f"Missing required fields in 1Password item: {missing_fields}")
            
            self.credentials = credentials
            logger.info("Successfully retrieved B2 credentials from 1Password")
            return credentials
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse 1Password response: {e}")
            raise B2AuthError("Invalid 1Password response format")
        except subprocess.TimeoutExpired:
            logger.error("1Password CLI command timed out")
            raise B2AuthError("1Password CLI timeout")
        except Exception as e:
            logger.error(f"Unexpected error retrieving credentials: {e}")
            raise B2AuthError(f"Credential retrieval failed: {e}")
    
    def authorize_b2(self) -> bool:
        """Authorize B2 CLI using retrieved credentials."""
        if not self.credentials:
            self.get_1password_credentials()
        
        try:
            # Authorize B2 CLI
            result = subprocess.run(
                [
                    Config.B2_CLI, "account", "authorize",
                    self.credentials['keyID'],
                    self.credentials['applicationKey']
                ],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                logger.error("B2 authorization failed")
                logger.error(f"Error: {result.stderr}")
                raise B2AuthError("B2 CLI authorization failed")
            
            logger.info("Successfully authorized B2 CLI")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("B2 authorization timed out")
            raise B2AuthError("B2 authorization timeout")
        except Exception as e:
            logger.error(f"Unexpected error during B2 authorization: {e}")
            raise B2AuthError(f"B2 authorization failed: {e}")
    
    def verify_b2_auth(self) -> bool:
        """Verify B2 authentication status."""
        try:
            result = subprocess.run(
                [Config.B2_CLI, "account", "get"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.warning("B2 authentication verification failed")
                return False
            
            logger.info("B2 authentication verified")
            return True
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.warning("B2 CLI not available or timed out during verification")
            return False
    
    def authenticate(self) -> bool:
        """Complete authentication flow: get credentials and authorize B2."""
        try:
            logger.info("Starting B2 authentication flow")
            
            # Check if already authenticated
            if self.verify_b2_auth():
                logger.info("Already authenticated with B2")
                return True
            
            # Get credentials and authorize
            self.get_1password_credentials()
            self.authorize_b2()
            
            # Verify authentication
            if not self.verify_b2_auth():
                raise B2AuthError("Authentication verification failed after authorization")
            
            logger.info("B2 authentication completed successfully")
            return True
            
        except B2AuthError:
            raise
        except Exception as e:
            logger.error(f"Authentication flow failed: {e}")
            raise B2AuthError(f"Authentication failed: {e}")
    
    def get_bucket_name(self) -> str:
        """Get the bucket name from credentials or config."""
        if self.credentials and self.credentials.get('Bucket'):
            return self.credentials['Bucket']
        return self.config.bucket_name


def authenticate_b2(config: Config) -> B2Auth:
    """Convenience function to authenticate with B2."""
    auth = B2Auth(config)
    auth.authenticate()
    return auth