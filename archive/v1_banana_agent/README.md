# Banana Agent v1 - Archived

This directory contains the original "Banana Agent" prototype that was built before pivoting to the MCP Chat Interface.

## What Was Built

### Features
- **ERD Image Upload**: Users could upload Entity-Relationship Diagrams
- **Gemini Vision Analysis**: Used Gemini 2.0 Flash to extract schema from ERD images
- **Dummy Data Generation**: Generated SQL CREATE TABLE and INSERT statements
- **LookML Generation**: Created Looker view and model files
- **Dashboard Design**: Proposed dashboard layouts based on schema

### Architecture
- **Frontend**: Next.js with Gemini-inspired light theme
- **Backend**: FastAPI with Gemini API integration
- **Agent Logic**: `agent_logic.py` - orchestrated the workflow
- **MCP Integration**: Used ephemeral stdio sessions to call Looker MCP Toolbox

### Why We Pivoted
The user wanted a more focused tool:
- Remove complexity of ERD uploads and image processing
- Focus purely on conversational interaction with Looker via MCP
- Create a Gemini-like chat interface for multi-turn conversations
- Direct access to MCP tool endpoints without intermediate layers

## Files Archived
- `agent_logic.py` - Original agent with analyze_requirements, generate_lookml, deploy_prototype
- `page_v1.tsx` - UI with ERD upload, single-prompt input
- `globals_v1.css` - Styling for v1 UI

## Date Archived
2026-01-30
