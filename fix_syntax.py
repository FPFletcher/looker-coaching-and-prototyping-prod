import re

file_path = 'apps/agent/mcp_agent.py'
with open(file_path, 'r') as f:
    content = f.read()

# Fix the import block
import_fix = """import os
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, AsyncGenerator
from anthropic import AsyncAnthropic
from google.oauth2 import credentials as google_credentials
from google.oauth2 import service_account
try:
    from anthropic import AsyncAnthropicVertex as _AnthropicVertex
except ImportError:
    _AnthropicVertex = None
import httpx"""

# We'll just replace everything from import os until import httpx
pattern = r"import os.*import httpx"
# Using re.DOTALL to match newlines
content = re.sub(pattern, import_fix, content, flags=re.DOTALL)

with open(file_path, 'w') as f:
    f.write(content)

print("Fixed imports syntax.")
