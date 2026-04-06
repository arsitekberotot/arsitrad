#!/usr/bin/env python3
"""
Quick runner for Pasal.id scraper.
Usage:
    python run_scraper.py --domain peraturan --type UU --max-pages 3 --list-only
    python run_scraper.py --domain peraturan --type UU --max-pages 5 --max-pdfs 10
"""

import sys
import os

# Add parent to path so scraper can find modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.pasal_scraper import main

if __name__ == "__main__":
    main()
