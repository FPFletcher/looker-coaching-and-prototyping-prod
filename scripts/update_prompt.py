
import os

file_path = 'apps/agent/mcp_agent.py'

new_block = [
    '            f"CRITICAL: DATA PRESENTATION PROTOCOLS:\\n"',
    '            f"When presenting ANY chart, dashboard, or query result, YOU MUST FOLLOW THIS STRICT INTERFACE ORDER:\\n"',
    '            f"1. **VISUALIZATION FIRST**: Output the `create_chart` or `create_dashboard` tool result FIRST. The chart MUST be the very first thing the user sees. Do NOT write any introduction before the chart.\\n"',
    '            f"2. **ANALYSIS SECOND**: Immediately below the visualization, provide the analysis in this strict format:\\n\\n"',
    '            ',
    '            f"   **🔎 INSIGHTS**\\n"',
    '            f"   - One sentence summarizing the bottom line impact.\\n"',
    '            f"   - *Example*: \'Revenue missed target by 8% due to low EMEA performance.\'\\n\\n"',
    '            ',
    '            f"   **📊 TRENDS**\\n"',
    '            f"   - The key factors, segments, or trends driving the insight.\\n"',
    '            f"   - *Example*: \'North America is stable (+2%), but Germany dropped 15% YoY.\'\\n\\n"',
    '            ',
    '            f"   **🎯 RECOMMENDATIONS**\\n"',
    '            f"   - Specific, execution-oriented recommendations.\\n"',
    '            f"   - *Example*: \'Review German pricing strategy\' or \'Reallocate ad spend to NA.\'\\n\\n"',
    '            ',
    '            f"   **❓ FOLLOW-UP QUESTIONS**\\n"',
    '            f"   - Suggest 2-3 specific questions the user might want to ask next to dig deeper.\\n"',
    '            f"   - *Example*: \'Why is the churn rate higher in Q3?\', \'Show me the breakdown by customer tier.\'\\n\\n"',
    '',
    '            f"**FORBIDDEN**: Do NOT simply describe the chart (e.g., \'The chart shows X is 10\'). This is useless. Provide ANALYSIS.\\n\\n"'
]

with open(file_path, 'r') as f:
    lines = f.readlines()

# Replace lines 1018 to 1035 (0-indexed: 1017 to 1035)
# Line 1018 in 1-based index is index 1017 in 0-based list
start_idx = 1017 
end_idx = 1035 

# Verify we are replacing the right block?
print(f"Replacing lines {start_idx+1}-{end_idx+1}:")
for i in range(start_idx, end_idx):
    print(lines[i].rstrip())

# Logic: Remove the old lines, insert new lines
# We need to add newlines to new_block items manually or join them
new_content_lines = [line + '\n' for line in new_block]

# Slice assignment
lines[start_idx:end_idx+1] = new_content_lines

with open(file_path, 'w') as f:
    f.writelines(lines)

print("Update complete.")
