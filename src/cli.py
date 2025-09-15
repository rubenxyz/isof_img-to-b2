#!/usr/bin/env python3
"""
Backblaze B2 Image Sync CLI

A Python tool that syncs images from USER-FILES/04.INPUT/ to a Backblaze B2 bucket,
generating individual link files for each uploaded image.
"""

import argparse
import sys
from pathlib import Path
from loguru import logger

from .sync import B2Sync
from .config import Config


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the application."""
    # Remove default handler
    logger.remove()
    
    # Add console handler
    log_level = "DEBUG" if verbose else "INFO"
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )


def main() -> int:
    """Main entry point for the B2 sync application."""
    parser = argparse.ArgumentParser(
        description="Backblaze B2 Image Sync - Sync images to B2 bucket with 1Password authentication",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.cli                    # Sync files to B2 bucket
  python -m src.cli sync               # Explicit sync operation  
  python -m src.cli sync --dry-run     # Preview sync without making changes
  python -m src.cli clean              # Remove all files from bucket (with confirmation)
  python -m src.cli clean --force      # Remove all files without confirmation
  python -m src.cli clean --dry-run    # Preview clean without making changes
  python -m src.cli init-config        # Create default configuration file
        """
    )
    
    parser.add_argument(
        '--config',
        type=Path,
        help='Path to configuration file (default: USER-FILES/01.CONFIG/b2_sync_config.yml)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Sync command
    sync_parser = subparsers.add_parser(
        'sync',
        help='Synchronize files from USER-FILES/04.INPUT/ to B2 bucket'
    )
    sync_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without making them'
    )
    
    # Clean command
    clean_parser = subparsers.add_parser(
        'clean',
        help='Remove all files from B2 bucket'
    )
    clean_parser.add_argument(
        '--force',
        action='store_true',
        help='Skip confirmation prompt'
    )
    clean_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview what would be deleted without making changes'
    )
    
    # Init-config command
    subparsers.add_parser(
        'init-config',
        help='Create default configuration file'
    )
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.verbose)
    
    # Load configuration
    config = Config(args.config) if args.config else Config()
    
    # Default to sync if no command specified
    if not args.command:
        args.command = 'sync'
        args.dry_run = False
    
    try:
        if args.command == 'init-config':
            # Create default configuration file
            config.save_config()
            config_path = config.config_file
            logger.info(f"Created default configuration file: {config_path}")
            logger.info("Please edit this file to set your B2 bucket name and 1Password item name")
            return 0
            
        elif args.command == 'sync':
            syncer = B2Sync(config)
            return syncer.sync_operation(dry_run=args.dry_run)
            
        elif args.command == 'clean':
            syncer = B2Sync(config)
            return syncer.clean_operation(force=args.force, dry_run=args.dry_run)
            
        else:
            parser.print_help()
            return 1
            
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())