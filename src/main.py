#!/usr/bin/env python3
"""Main entry point for B2 Sync tool when run as src.main module."""

import sys
from .cli import main

if __name__ == '__main__':
    sys.exit(main())