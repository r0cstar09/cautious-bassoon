# Environment Variables Setup

This project uses environment variables for all secrets and configuration. Follow these steps to set up your environment.

## Quick Setup

1. **Create a `.env` file** in the project root directory:

```bash
touch .env
```

2. **Add your credentials** to the `.env` file:

```bash
# Azure OpenAI Configuration (Required)
AZURE_OPENAI_API_KEY=your_azure_openai_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource-name.cognitiveservices.azure.com
AZURE_OPENAI_CHAT_DEPLOYMENT=your-deployment-name
AZURE_OPENAI_API_VERSION=2023-05-15

# Email Configuration (Optional - for email notifications)
EMAIL_FROM=your-email@example.com
EMAIL_TO=recipient@example.com
EMAIL_PASSWORD=your-app-password
EMAIL_SMTP_SERVER=smtp.mail.me.com
EMAIL_SMTP_PORT=587
```

## Required Variables

- `AZURE_OPENAI_API_KEY` - Your Azure OpenAI API key
- `AZURE_OPENAI_ENDPOINT` - Your Azure OpenAI endpoint URL
- `AZURE_OPENAI_CHAT_DEPLOYMENT` - The name of your chat model deployment

## Optional Variables

- `AZURE_OPENAI_API_VERSION` - API version (defaults to "2023-05-15")
- `EMAIL_FROM` - Sender email address
- `EMAIL_TO` - Recipient email address
- `EMAIL_PASSWORD` - Email password or app password
- `EMAIL_SMTP_SERVER` - SMTP server (defaults to "smtp.mail.me.com")
- `EMAIL_SMTP_PORT` - SMTP port (defaults to 587)
- `RESUME_PROMPT` - Custom prompt for resume generation
- `COVER_LETTER_PROMPT` - Custom prompt for cover letter generation

## How Environment Variables Are Loaded

The project uses `python-dotenv` to automatically load variables from the `.env` file when you run the script. The `load_dotenv()` function in `main.py` will read your `.env` file.

## Running the Script

### Option 1: Direct Python (recommended)
```bash
python3 -m src.rss_job_app.main --feed "YOUR_RSS_FEED_URL"
```

The `.env` file will be automatically loaded.

### Option 2: Using the wrapper script
```bash
./scripts/run_with_env.sh --feed "YOUR_RSS_FEED_URL"
```

This script explicitly loads the `.env` file and provides a sanity check.

### Option 3: Manual environment variables
You can also set environment variables directly in your shell:

```bash
export AZURE_OPENAI_API_KEY="your-key"
export AZURE_OPENAI_ENDPOINT="https://your-endpoint"
export AZURE_OPENAI_CHAT_DEPLOYMENT="your-deployment"
python3 -m src.rss_job_app.main --feed "YOUR_RSS_FEED_URL"
```

## Security Note

- The `.env` file is already in `.gitignore` - it will NOT be committed to git
- Never commit your `.env` file or share it publicly
- Keep your API keys secure

