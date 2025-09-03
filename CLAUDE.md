# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a collection of automation scripts for **QingLong Panel** (青龙面板), a popular task automation platform. The repository contains both JavaScript and Python scripts designed for scheduled execution in the QingLong environment.

## Architecture

### Directory Structure
```
ScriptsForQinglong/
├── Py/                    # Python scripts
│   ├── utils/            # Python utility modules
│   │   ├── pyEnv.py      # Environment variable handling
│   │   ├── notify.py     # Notification system
│   │   └── js_reverse/   # JavaScript decompilation tools
│   ├── aiMorningBrief.py # AI-powered morning briefing
│   ├── hackerNews.py     # Hacker News scraper with AI summary
│   └── [other scripts]
├── Js/                    # JavaScript scripts
│   ├── utils/            # JavaScript utility modules
│   │   ├── env.js        # Environment utilities
│   │   ├── common.js     # Common utilities (HTTP requests, UA rotation, MD5)
│   │   ├── envCheck.js   # Environment validation
│   │   ├── initScript.js # Script initialization template
│   │   └── sendNotify.js # Notification system
│   ├── wx_mini/          # WeChat mini-program scripts
│   └── other/
└── requirements.txt      # Python dependencies
```

### Key Components

**JavaScript Layer:**
- Uses CommonJS modules with dependency on `axios` for HTTP requests
- Provides unified environment management through `env.js`
- Includes sophisticated user-agent rotation for anti-detection
- Built-in notification system via `sendNotify.js`

**Python Layer:**
- Async/await pattern for web scraping with `aiohttp` and `httpx`
- AI integration using OpenAI-compatible APIs (Zhipu AI)
- Structured logging with `loguru`
- Environment variable management through `pyEnv.py`
- BeautifulSoup for HTML parsing

### Common Patterns

**JavaScript Scripts:**
- Always start with `const {default: axios} = require("axios");`
- Use `const {sendRequest, getRandomUserAgent} = require("./utils/common");`
- Initialize with `const $ = new Env("[app-name]");`
- Include notification: `const notify = require("./utils/sendNotify");`

**Python Scripts:**
- Use `utils.pyEnv as env` for environment variables
- Implement `logger.remove()` and custom logging configuration
- Follow async/await pattern with `async def main()`
- Include AI API key configuration: `ZHIPU_API_KEY` and `ZHIPU_BASE_URL`
- Add script metadata with cron scheduling at the top

## Development Commands

### JavaScript Development
```bash
# Install dependencies (in root directory)
pnpm install

# Test individual script (navigate to script directory)
node script-name.js
```

### Python Development
```bash
# Install Python dependencies
pip install -r requirements.txt

# Run individual script
python script-name.py
```

### QingLong Panel Integration
To add scripts to QingLong panel, use:
```bash
ql repo https://github.com/MoLing-Dong/ScriptsForQinglong.git "" "utils" "utils" "main"
```

## Environment Setup

### Required Environment Variables
Most scripts require these environment variables to be set in QingLong:
- `ZHIPU_API_KEY`: Zhipu AI API key for AI summarization
- `ZHIPU_BASE_URL`: Zhipu AI API base URL
- Various platform-specific tokens and credentials

### Dependencies
- **JavaScript**: `axios` (automatically installed via package.json)
- **Python**: Listed in `requirements.txt` including `aiohttp`, `httpx`, `beautifulsoup4`, `loguru`, `openai`, `fake_useragent`

## Script Categories

1. **AI-Powered Scripts**: `aiMorningBrief.py`, `hackerNews.py` - Use AI for content summarization
2. **Web Scrapers**: Various scripts for different platforms and APIs
3. **Utilities**: Common functions used across multiple scripts
4. **Notification Systems**: Standardized notification delivery across platforms

## Important Notes

- All scripts are designed for QingLong Panel environment and scheduled execution
- Scripts include anti-detection measures (user-agent rotation, random delays)
- AI-powered scripts use Zhipu AI API (OpenAI-compatible)
- Notification system supports multiple channels
- Scripts follow consistent error handling and logging patterns