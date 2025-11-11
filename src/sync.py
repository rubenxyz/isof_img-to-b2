"""Main B2 sync operations."""

import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from loguru import logger

from .auth import B2AuthError, authenticate_b2
from .config import Config
from .utils import (
    create_timestamped_output_dir,
    generate_failure_report,
    generate_json_log,
    generate_link_files,
    parse_b2_sync_output,
    run_b2_command
)


class B2Sync:
    """Handle B2 sync operations."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize with configuration."""
        self.config = config or Config()
    
    def _validate_environment(self) -> bool:
        """Validate environment and log errors."""
        if not Config.validate_environment():
            logger.error("Environment validation failed")
            return False
        return True
    
    def _prepare_sync_command(self, input_path: Path, bucket_name: str, dry_run: bool) -> List[str]:
        """Build the B2 sync command with all necessary options."""
        sync_command = [
            Config.B2_CLI, "sync",
            "--threads", "4",  # Hardcoded safe thread count to avoid upload token conflicts
            "--replace-newer",  # Allow older local files to replace newer destination files
            "--delete",  # Delete files from destination that are not in source (true mirroring)
        ]
        
        # Add exclusion patterns
        for pattern in self.config.exclude_patterns:
            sync_command.extend(["--exclude-regex", pattern])
        
        sync_command.extend([
            str(input_path),
            f"b2://{bucket_name}/"
        ])
        
        if dry_run:
            sync_command.append("--dry-run")
            logger.info("DRY RUN MODE - No actual changes will be made")
        
        logger.info(f"Executing sync command: {' '.join(sync_command)}")
        return sync_command
    
    def _handle_sync_error(self, output_dir: Path, return_code: int, stderr: str) -> int:
        """Handle sync errors and generate failure report."""
        logger.error(f"B2 sync failed with return code {return_code}")
        logger.error(f"Error output: {stderr}")
        
        errors = [{
            'file': 'sync_operation',
            'error_type': 'B2SyncFailure',
            'error_message': stderr,
            'timestamp': datetime.now().isoformat()
        }]
        
        generate_failure_report(output_dir, errors, "sync")
        return return_code
    
    def _generate_sync_outputs(self, output_dir: Path, files_processed: List[Dict[str, str]], 
                              bucket_name: str, execution_time: float) -> None:
        """Generate all output files for the sync operation."""
        generate_json_log(
            output_dir=output_dir,
            operation="sync",
            files_processed=files_processed,
            errors=[],
            execution_time=execution_time,
            bucket_name=bucket_name
        )
        
        generate_link_files(output_dir, files_processed, bucket_name)
    
    def _log_sync_summary(self, execution_time: float, files_processed: List[Dict[str, str]], 
                         output_dir: Path) -> None:
        """Log summary information for the sync operation."""
        logger.info(f"Sync completed successfully in {execution_time:.2f} seconds")
        logger.info(f"Files processed: {len(files_processed)}")
        logger.info(f"Output directory: {output_dir}")
    
    def _verify_bucket_access(self, bucket_name: str) -> int:
        """Verify bucket exists and is accessible."""
        bucket_check_command = [Config.B2_CLI, "ls", f"b2://{bucket_name}"]
        return_code, stdout, stderr = run_b2_command(bucket_check_command)
        
        if return_code != 0:
            logger.error(f"Failed to access bucket '{bucket_name}'")
            logger.error(f"Error: {stderr}")
        
        return return_code
    
    def _get_file_count(self, bucket_name: str) -> Tuple[int, int]:
        """Get count of files in bucket."""
        list_command = [Config.B2_CLI, "ls", "--long", f"b2://{bucket_name}"]
        return_code, stdout, stderr = run_b2_command(list_command)
        
        if return_code != 0:
            logger.error("Failed to list bucket contents")
            logger.error(f"Error: {stderr}")
            return return_code, 0
        
        file_count = sum(1 for line in stdout.split('\n') 
                        if line.strip() and not line.startswith('--'))
        return return_code, file_count
    
    def _get_user_confirmation(self, file_count: int, bucket_name: str, force: bool, dry_run: bool) -> bool:
        """Get user confirmation for deletion."""
        if dry_run:
            logger.info(f"DRY RUN: Would delete {file_count} files from bucket '{bucket_name}'")
            return False
        
        if not force:
            print(f"\nWARNING: This will permanently delete {file_count} files from bucket '{bucket_name}'")
            response = input("Are you sure you want to continue? (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                logger.info("Clean operation cancelled by user")
                return False
        
        return True
    
    def _execute_clean_command(self, bucket_name: str) -> tuple[int, str, str]:
        """Execute the bucket cleaning command."""
        clean_command = [
            Config.B2_CLI, "rm",
            "--versions",
            "--recursive",
            f"b2://{bucket_name}"
        ]
        
        logger.info(f"Executing clean command: {' '.join(clean_command)}")
        return run_b2_command(clean_command)
    
    def _cleanup_unfinished_files(self, bucket_name: str) -> None:
        """Clean up any unfinished large files."""
        cancel_command = [Config.B2_CLI, "cancel-all-unfinished-large-files", bucket_name]
        cancel_return_code, _, _ = run_b2_command(cancel_command)
        
        if cancel_return_code == 0:
            logger.info("Cleaned up unfinished large files")
        
    def sync_operation(self, dry_run: bool = False) -> int:
        """Execute sync operation to mirror input directory to B2 bucket."""
        start_time = time.time()
        
        try:
            logger.info("Starting B2 sync operation")
            
            # Validate environment
            if not self._validate_environment():
                return 1
            
            # Authenticate with B2
            auth = authenticate_b2(self.config)
            bucket_name = auth.get_bucket_name()
            
            # Create output directory with timestamp
            output_dir = create_timestamped_output_dir(Config.get_output_path())
            
            # Prepare sync command
            input_path = Config.get_input_path()
            sync_command = self._prepare_sync_command(input_path, bucket_name, dry_run)
            
            # Execute sync
            return_code, stdout, stderr = run_b2_command(sync_command, self.config.sync_timeout)
            
            execution_time = time.time() - start_time
            
            if return_code != 0:
                return self._handle_sync_error(output_dir, return_code, stderr)
            
            # Parse sync output
            files_processed = parse_b2_sync_output(stdout)
            
            # Generate output files
            self._generate_sync_outputs(output_dir, files_processed, bucket_name, execution_time)
            
            # Log summary
            self._log_sync_summary(execution_time, files_processed, output_dir)
            
            return 0
            
        except B2AuthError as e:
            logger.error(f"Authentication error: {e}")
            return 1
        except Exception as e:
            logger.error(f"Unexpected error during sync: {e}")
            return 1
    
    def clean_operation(self, force: bool = False, dry_run: bool = False) -> int:
        """Execute clean operation to remove all files from B2 bucket."""
        start_time = time.time()
        
        try:
            logger.info("Starting B2 clean operation")
            
            # Validate environment
            if not self._validate_environment():
                return 1
            
            # Authenticate with B2
            auth = authenticate_b2(self.config)
            bucket_name = auth.get_bucket_name()
            
            # Create output directory
            output_dir = create_timestamped_output_dir(Config.get_output_path())
            
            # Verify bucket access
            if self._verify_bucket_access(bucket_name) != 0:
                return 1
            
            # Get file count
            return_code, file_count = self._get_file_count(bucket_name)
            if return_code != 0:
                return return_code
            
            # Get user confirmation
            if not self._get_user_confirmation(file_count, bucket_name, force, dry_run):
                return 0
            
            # Execute clean command
            return_code, stdout, stderr = self._execute_clean_command(bucket_name)
            
            execution_time = time.time() - start_time
            
            if return_code != 0:
                logger.error(f"B2 clean failed with return code {return_code}")
                logger.error(f"Error output: {stderr}")
                return return_code
            
            # Clean up unfinished files
            self._cleanup_unfinished_files(bucket_name)
            
            # Generate log
            files_processed = [{
                'local_path': '',
                'b2_key': f'bucket://{bucket_name}',
                'action': 'delete_all',
                'status': 'success',
                'file_count': file_count
            }]
            
            generate_json_log(
                output_dir=output_dir,
                operation="clean",
                files_processed=files_processed,
                errors=[],
                execution_time=execution_time,
                bucket_name=bucket_name,
                files_deleted=file_count
            )
            
            logger.info(f"Clean completed successfully in {execution_time:.2f} seconds")
            logger.info(f"Files deleted: {file_count}")
            logger.info(f"Output directory: {output_dir}")
            
            return 0
            
        except B2AuthError as e:
            logger.error(f"Authentication error: {e}")
            return 1
        except Exception as e:
            logger.error(f"Unexpected error during clean: {e}")
            return 1