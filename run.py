#!/usr/bin/env python3
"""Convenience launcher for the B2 Sync tool.

Usage:
  python run.py [--verbose] [--config PATH] {sync,clean,init-config} [options]
"""
import sys
from src.cli import main

if __name__ == "__main__":
    sys.exit(main())
