"""
Utility module to load system prompts from external files.
"""

import os
from typing import Optional

PROMPTS_DIR = "system_prompts"
DEFAULT_VERSION = "v1.0"

def load_prompt(agent_name: str, version: Optional[str] = None) -> str:
    """
    Load a system prompt from file.
    
    Args:
        agent_name: Name of the agent (e.g., 'greeting', 'interviewer')
        version: Version of prompts to use (defaults to v1.0)
    
    Returns:
        The system prompt as a string
    """
    version = version or DEFAULT_VERSION
    prompt_path = os.path.join(PROMPTS_DIR, version, f"{agent_name}_prompt.txt")
    
    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()

def list_available_prompts(version: Optional[str] = None) -> list:
    """List all available prompt files for a version."""
    version = version or DEFAULT_VERSION
    version_dir = os.path.join(PROMPTS_DIR, version)
    
    if not os.path.exists(version_dir):
        return []
    
    prompts = [
        f.replace('_prompt.txt', '') 
        for f in os.listdir(version_dir) 
        if f.endswith('_prompt.txt')
    ]
    return prompts
