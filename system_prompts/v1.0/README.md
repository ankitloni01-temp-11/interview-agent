# System Prompts - v1.0

## Overview
System prompts extracted from interview agent on 2026-02-10

## Files
- `greeting_prompt.txt` - Prompt for Greeting
- `interviewer_prompt.txt` - Prompt for Interviewer
- `feedback_prompt.txt` - Prompt for Feedback
- `kpi_prompt.txt` - Prompt for Kpi

## Usage
Load prompts in your code:
```python
def load_prompt(agent_name, version="v1.0"):
    prompt_path = f"system_prompts/{version}/{agent_name}_prompt.txt"
    with open(prompt_path, 'r') as f:
        return f.read()
```
