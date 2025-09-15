"""Utility functions for B2 sync operations."""

import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from loguru import logger

from .config import Config

# Constants
DEFAULT_TIMEOUT_SECONDS = 1800  # 30 minutes
DEFAULT_B2_ENDPOINT = "f003"  # Default Backblaze endpoint


def create_timestamped_output_dir(base_dir: Path) -> Path:
    """Create a timestamped output directory for this run."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = base_dir / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created output directory: {output_dir}")
    return output_dir


def parse_b2_sync_output(output: str) -> List[Dict[str, str]]:
    """Parse B2 sync command output to extract file information."""
    # Define patterns and their handlers
    SYNC_PATTERNS = {
        'upload': (r'upload:\s+(.+?)\s+->\s+b2://[^/]+/(.+)', True),  # (pattern, has_local_path)
        'update': (r'update:\s+(.+?)\s+->\s+b2://[^/]+/(.+)', True),
        'delete': (r'delete:\s+b2://[^/]+/(.+)', False),
        'skip': (r'skip:\s+(.+?)\s+->\s+b2://[^/]+/(.+)', True),
    }
    
    files = []
    lines = output.strip().split('\n')
    sync_time = datetime.now().isoformat()
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Try each pattern
        for action, (pattern, has_local_path) in SYNC_PATTERNS.items():
            match = re.match(pattern, line)
            if match:
                if has_local_path:
                    local_path = match.group(1)
                    b2_key = match.group(2)
                else:
                    local_path = ''
                    b2_key = match.group(1)
                
                files.append({
                    'local_path': local_path,
                    'b2_key': b2_key,
                    'action': action,
                    'status': 'success',
                    'sync_time': sync_time
                })
                break
    
    return files


def get_actual_download_urls(bucket_name: str) -> List[Tuple[str, str]]:
    """Get actual download URLs from B2 for all files in the bucket.
    
    Returns:
        List of tuples: (download_url, relative_path)
    """
    url_path_pairs = []
    try:
        # Get list of files in bucket (recursive to get all files in subdirectories)
        list_command = [Config.B2_CLI, "ls", "--recursive", f"b2://{bucket_name}"]
        return_code, stdout, stderr = run_b2_command(list_command)
        
        if return_code != 0:
            logger.error(f"Failed to list bucket contents: {stderr}")
            return url_path_pairs
        
        # For each file, construct the download URL
        # The URL format is: https://{endpoint}.backblazeb2.com/file/{bucket_name}/{filename}
        # We need to determine the correct endpoint (f001, f003, etc.)
        
        # Try to get the endpoint from account info
        account_command = [Config.B2_CLI, "account", "get"]
        account_return_code, account_stdout, account_stderr = run_b2_command(account_command)
        
        endpoint = DEFAULT_B2_ENDPOINT  # Default fallback
        if account_return_code == 0:
            try:
                account_data = json.loads(account_stdout)
                download_url = account_data.get('downloadUrl', '')
                # Extract endpoint from URL: https://f003.backblazeb2.com
                endpoint_match = re.search(r'https://([^.]+)\.backblazeb2\.com', download_url)
                if endpoint_match:
                    endpoint = endpoint_match.group(1)
            except json.JSONDecodeError:
                pass
        
        # Now construct URLs for all files using the correct endpoint
        for line in stdout.strip().split('\n'):
            if line.strip():
                # The filename here is actually the full path in the bucket
                file_path = line.strip()
                # Skip directories (they end with /)
                if file_path.endswith('/'):
                    continue
                download_url = f"https://{endpoint}.backblazeb2.com/file/{bucket_name}/{file_path}"
                url_path_pairs.append((download_url, file_path))
                    
    except Exception as e:
        logger.error(f"Error getting download URLs: {e}")
    
    return url_path_pairs


def _ensure_subdirectory(output_dir: Path, file_path: Path) -> Path:
    """Ensure subdirectory exists for the given file path."""
    if file_path.parent != Path('.'):
        subdirectory = output_dir / file_path.parent
        subdirectory.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created subdirectory: {subdirectory}")
        return subdirectory
    return output_dir


def _get_link_file_path(output_dir: Path, file_path: Path, link_filename: str) -> Path:
    """Get the full path for a link file, considering subdirectories."""
    if file_path.parent != Path('.'):
        return output_dir / file_path.parent / link_filename
    return output_dir / link_filename


def _create_link_file(output_dir: Path, file_path: Path, url: str) -> bool:
    """Create a single link file with the given URL."""
    try:
        # Ensure subdirectory exists
        _ensure_subdirectory(output_dir, file_path)
        
        # Create the text file name and path
        base_name = file_path.stem
        link_filename = f"{base_name}.txt"
        link_file_path = _get_link_file_path(output_dir, file_path, link_filename)
        
        # Write the URL to the file
        with open(link_file_path, 'w') as f:
            f.write(url)
        
        logger.debug(f"Created link file: {link_file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to create link file for {file_path}: {e}")
        return False


def generate_link_files(output_dir: Path, files_processed: List[Dict[str, str]], bucket_name: str) -> Path:
    """Generate individual link files for each uploaded file with B2 friendly URLs, preserving directory structure."""
    # Get actual download URLs from B2 with relative paths
    url_path_pairs = get_actual_download_urls(bucket_name)
    
    files_created = 0
    
    if url_path_pairs:
        # Create individual text files for each URL, preserving directory structure
        for url, relative_path in url_path_pairs:
            file_path = Path(relative_path)
            if _create_link_file(output_dir, file_path, url):
                files_created += 1
    else:
        logger.warning("No URLs found, using fallback method")
        # Fallback to files_processed if available
        for file_info in files_processed:
            b2_key = file_info.get('b2_key', '')
            if b2_key and file_info.get('action') in ['upload', 'update']:
                file_path = Path(b2_key)
                # Generate the friendly URL (using f003 as default)
                public_url = f"https://f003.backblazeb2.com/file/{bucket_name}/{b2_key}"
                if _create_link_file(output_dir, file_path, public_url):
                    files_created += 1
    
    logger.info(f"Generated {files_created} individual link files in: {output_dir}")
    return output_dir


def generate_json_log(
    output_dir: Path,
    operation: str,
    files_processed: List[Dict[str, str]],
    errors: List[Dict[str, str]],
    execution_time: float,
    **kwargs
) -> Path:
    """Generate comprehensive JSON log file."""
    timestamp = datetime.now().isoformat()
    
    # Calculate statistics
    stats = {
        "files_uploaded": len([f for f in files_processed if f.get('action') == 'upload']),
        "files_updated": len([f for f in files_processed if f.get('action') == 'update']),
        "files_deleted": len([f for f in files_processed if f.get('action') == 'delete']),
        "files_skipped": len([f for f in files_processed if f.get('action') == 'skip']),
        "files_failed": len([f for f in files_processed if f.get('status') == 'failed']),
    }
    
    # Add file size information for uploaded/updated files
    for file_info in files_processed:
        if file_info.get('action') in ['upload', 'update'] and file_info.get('local_path'):
            local_path = Path(file_info['local_path'])
            if local_path.exists():
                try:
                    file_info['file_size_bytes'] = local_path.stat().st_size
                except Exception:
                    file_info['file_size_bytes'] = 0
    
    log_data = {
        "run_metadata": {
            "timestamp": timestamp,
            "operation": operation,
            "total_files": len(files_processed),
            "execution_time_seconds": execution_time,
            **stats,
            **kwargs
        },
        "files_processed": files_processed,
        "errors": errors
    }
    
    log_file = output_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{operation}_log.json"
    
    with open(log_file, 'w') as f:
        json.dump(log_data, f, indent=2)
    
    logger.info(f"Generated JSON log: {log_file}")
    return log_file


def generate_failure_report(output_dir: Path, errors: List[Dict[str, str]], operation: str) -> Optional[Path]:
    """Generate human-readable failure report if there are errors."""
    if not errors:
        return None
    
    timestamp = datetime.now()
    failure_file = output_dir / "FAILURE.md"
    
    with open(failure_file, 'w') as f:
        f.write("# Sync Failure Report\n")
        f.write(f"**Date**: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Operation**: {operation}\n\n")
        
        f.write("## Summary\n")
        f.write(f"- **Failed Files**: {len(errors)}\n\n")
        
        f.write("## Failed Files\n")
        for error in errors:
            file_path = error.get('file', 'Unknown')
            error_type = error.get('error_type', 'Unknown')
            error_message = error.get('error_message', 'No details available')
            
            f.write(f"### {file_path}\n")
            f.write(f"- **Error**: {error_message}\n")
            f.write(f"- **Type**: {error_type}\n\n")
        
        f.write("## Next Steps\n")
        f.write("1. Fix the identified issues with failed files\n")
        f.write("2. Re-run the sync script to update changes\n")
    
    logger.warning(f"Generated failure report: {failure_file}")
    return failure_file


def run_b2_command(command: List[str], timeout: Optional[int] = None) -> Tuple[int, str, str]:
    """Run a B2 CLI command and return results."""
    if timeout is None:
        timeout = DEFAULT_TIMEOUT_SECONDS
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        logger.error(f"B2 command timed out after {timeout} seconds")
        return -1, "", "Command timed out"
    except Exception as e:
        logger.error(f"Failed to run B2 command: {e}")
        return -1, "", str(e)


