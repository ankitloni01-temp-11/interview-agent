import os
from pathlib import Path

# Get the project root directory
project_root = Path(__file__).parent.parent
env_file = project_root / '.env'

# Read .env file manually
API_KEY = None
SERPER_API_KEY = None

if env_file.exists():
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if key == 'GEMINI_API_KEY':
                        API_KEY = value
                    elif key == 'SERPER_API_KEY':
                        SERPER_API_KEY = value

if API_KEY:
    print(f"[✓] GEMINI_API_KEY loaded from .env ({len(API_KEY)} chars)")
else:
    print("[⚠] GEMINI_API_KEY not found in .env file!")

if SERPER_API_KEY:
    print(f"[✓] SERPER_API_KEY loaded from .env ({len(SERPER_API_KEY)} chars)")
else:
    print("[⚠] SERPER_API_KEY not found in .env file!")

# Also try environment variables
if not API_KEY:
    API_KEY = os.getenv("GEMINI_API_KEY")
if not SERPER_API_KEY:
    SERPER_API_KEY = os.getenv("SERPER_API_KEY")
