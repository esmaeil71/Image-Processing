import sys
from pathlib import Path

# Ensure `import app` resolves to backend/app
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
