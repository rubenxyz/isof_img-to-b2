#!/usr/bin/env python3
"""
Backblaze B2 Image Sync CLI

A Python tool that syncs images from USER-FILES/04.INPUT/ to a Backblaze B2 bucket,
generating individual link files for each uploaded image.
"""

import sys
from loguru import logger

from .sync import B2Sync
from .config import Config


def setup_logging() -> None:
    """Configure logging for the application."""
    # Remove default handler
    logger.remove()
    
    # Add console handler
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )


def main() -> int:
    """Main entry point for the B2 sync application."""
    # Set up logging
    setup_logging()
    
    # Load default configuration
    config = Config()
    
    try:
        # Always run sync operation with live behavior (no dry run)
        syncer = B2Sync(config)
        return syncer.sync_operation(dry_run=False)
        
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())