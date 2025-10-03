#!/usr/bin/env python
import sys
from src.main import main

if __name__ == "__main__":
    # Add src to path to allow for module imports
    sys.path.insert(0, 'src')
    main()