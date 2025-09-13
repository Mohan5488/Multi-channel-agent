# Multichannel Agent

A LangGraph-based agent that can send emails and post to LinkedIn using human-in-the-loop workflows.

## Features

- **Intent Detection**: Automatically determines if user wants to send email or post to LinkedIn
- **Content Extraction**: Uses LLM to extract recipients, subjects, and content from natural language
- **Human-in-the-Loop**: Interrupts workflow when critical information is missing
- **Human Approval**: Shows previews and allows editing before sending/posting
- **Direct Integration**: Directly sends emails and posts to LinkedIn without external protocols
- **Simplified State**: Clean, minimal state management with only 11 fields

## Architecture

```
User Input → Intent Detection → Content Composition → Human Gate → Direct Execution
```

### Workflow Nodes

1. **Intent Node**: Detects email vs LinkedIn vs chat intent
2. **Compose Email**: Extracts email details (to, subject, body) with human-in-the-loop
3. **Compose LinkedIn**: Extracts LinkedIn post content with human-in-the-loop
4. **Human Gate**: Shows previews and handles approval/editing
5. **Send Email**: Executes email sending functionality
6. **Post LinkedIn**: Executes LinkedIn posting functionality
7. **Chat Node**: Handles general conversation and chat interactions
8. **End Node**: Workflow completion and cleanup
9. **Tool Node**: Additional tool utilities and helpers

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

```bash
export OPENAI_API_KEY="your-openai-api-key"

# For email sending (optional)
export SENDER_EMAIL="your-email@example.com"
export SMTP_APP_PASSWORD="your-app-password"

# For LinkedIn posting (optional)
export LINKEDIN_ACCESS_TOKEN="your-linkedin-token"
export LINKEDIN_PERSON_URN="your-linkedin-urn"

# For web search (optional)
export TAVILY_API_KEY="your-tavily-api-key"
```

## Project Structure

```
mcp-multichannel-agent/
├── data/                         # Data directory
├── env/                          # Virtual environment
├── src/
│   └── agent/
│       ├── __init__.py           # Package initialization
│       ├── state.py              # Simplified state schema
│       ├── graph.py              # LangGraph workflow definition
│       ├── run.py                # CLI entry point
│       ├── nodes/
│       │   ├── chat.py           # Chat node for general conversation
│       │   ├── compose_email.py  # Email composition + extraction
│       │   ├── compose_linkedin.py # LinkedIn composition + extraction
│       │   ├── end.py            # End node for workflow completion
│       │   ├── human_gate.py     # Human approval and editing
│       │   ├── intent.py         # Intent detection (email vs LinkedIn)
│       │   ├── post_linkedin.py  # LinkedIn posting functionality
│       │   ├── send_email.py     # Email sending functionality
│       │   └── tools.py          # Tool utilities
│       └── tools/                # 
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## State Schema

The simplified state contains only 11 fields:

```python
{
    "user_prompt": "Original user input",
    "intent": "email" or "linkedin",
    "to": "Email recipient",
    "subject": "Email subject",
    "body": "Email body",
    "text": "LinkedIn post text",
    "needs_input": False,
    "human_message": None,
    "approved": None,
    "result": None,
    "error": None
}
```

## Human-in-the-Loop Workflow

1. **Intent Detection**: Determines email vs LinkedIn
2. **Content Extraction**: Extracts details from user prompt
3. **Interrupt if Missing**: Asks human for missing critical information
4. **Content Composition**: Creates final content
5. **Human Approval**: Shows preview and asks for approval/editing
6. **Direct Execution**: Sends email or posts to LinkedIn directly

## Direct Integration Tools

The agent directly integrates with these services:

- **Email Sending**: Direct SMTP integration for sending emails
- **LinkedIn Posting**: Direct API integration for posting to LinkedIn
- **Content Management**: Built-in content extraction and composition

## Error Handling

- **Graceful Fallbacks**: Falls back to regex extraction if LLM fails
- **Human Recovery**: Interrupts for human input when critical info is missing
- **Error Propagation**: Passes errors through state for proper handling
- **API Error Handling**: Handles email and LinkedIn API errors gracefully

## Troubleshooting

### Common Issues

#### OpenAI API Key Error (401 Authentication Error)
```
❌ Error code: 401 - Incorrect API key provided
```

**Solution:**
1. Verify your OpenAI API key is correct:
   ```bash
   echo $OPENAI_API_KEY
   ```
2. Set the API key if not set:
   ```bash
   export OPENAI_API_KEY='your-actual-api-key-here'
   ```
3. Or add to `.env` file:
   ```
   OPENAI_API_KEY=your-actual-api-key-here
   ```

#### Variable Scope Error
```
⚠️ Could not reset state: name 'app' is not defined
```

**Solution:** This is a cleanup error that occurs after the main API error. Fix the API key issue first.

#### Missing Dependencies
```bash
pip install -r requirements.txt
```

#### Environment Setup
Make sure you're in the correct virtual environment:
```bash
source env/bin/activate  # On macOS/Linux
```

## Development

### Adding New Channels

1. Add new intent detection in `intent.py`
2. Create composition node in `nodes/`
3. Add routing in `graph.py`
4. Create execution node (e.g., `send_email.py`, `post_linkedin.py`)
5. Update human gate to handle new channel

### Testing New Features

1. Test individual components
2. Test full workflow integration
3. Test error scenarios
4. Test human-in-the-loop interactions

## License

MIT License
