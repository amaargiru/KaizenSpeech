import sys
from pathlib import Path

# Make project modules importable no matter from which directory pytest is run
sys.path.insert(0, str(Path(__file__).parents[1]))
