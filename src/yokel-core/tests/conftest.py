import os
import sys
from pathlib import Path

current_dir = Path(__file__).parent
module_paths = [
    current_dir / "..",  # The current project under test
]

for path in module_paths:
    abs_path = path.resolve()  # Get absolute path
    if str(abs_path) not in sys.path:
        sys.path.insert(0, str(abs_path))


sys.path.insert(0, os.path.dirname(__file__))
