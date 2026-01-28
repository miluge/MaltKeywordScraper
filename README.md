# Malt Keyword Scraper

Automated scraper that extracts keyword analytics data from Malt freelancer profiles and syncs the data to Google Sheets for analysis and tracking.

## Features

- **Web Scraping**: Automatically scrapes keyword analytics from Malt dashboard using Playwright
- **Session Persistence**: Maintains authentication sessions to avoid repeated logins
- **Data Extraction**: Extracts keyword performance metrics including:
  - Keyword names
  - Number of appearances
  - Search ranking positions
- **Google Sheets Integration**: Automatically syncs scraped data to a Google Sheet with timestamps
- **Error Handling**: Robust logging and error handling for reliability
- **Stealth Mode**: Uses Playwright Stealth plugin to avoid detection

## Prerequisites

- Python 3.8 or higher
- Google Cloud Project with Google Sheets API enabled
- Service Account credentials (JSON key file)
- Malt freelancer account

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd MaltKeywordScraper
```

### 2. Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows:
```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Setup Google Sheets API

1. Create a Google Cloud Project
2. Enable the Google Sheets API
3. Create a Service Account and download the JSON key file
4. Save the credentials file as `credentials.json` in the project root

### 5. Configure Environment Variables

Create a `.env` file in the project root:

```env
SPREADSHEET_ID=your_google_spreadsheet_id_here
```

Get your Spreadsheet ID from the URL: `https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit`

### 6. Authenticate with Malt

Run the scraper once to create the authentication session:

```bash
python scraper.py
```

This will open a browser window. Log in to your Malt account. The session will be saved to `auth.json` for future use.

## Usage

### Basic Usage

```bash
python scraper.py
```

This will:
1. Load your Malt session from `auth.json`
2. Navigate to your analytics dashboard
3. Extract all keyword data
4. Sync the data to your Google Sheet with the current date

### Scheduling (Optional)

To run the scraper on a schedule, use `cron` (Linux/macOS) or Task Scheduler (Windows).

#### Linux/macOS Cron Example

```bash
# Edit crontab
crontab -e

# Add this line to run daily at 9 AM
0 9 * * * cd /path/to/MaltKeywordScraper && source .venv/bin/activate && python scraper.py
```

## Project Structure

```
MaltKeywordScraper/
├── scraper.py           # Main scraper script
├── requirements.txt     # Python dependencies
├── .gitignore          # Git ignore rules
├── README.md           # This file
├── .env               # Environment variables (not committed)
├── auth.json          # Playwright auth session (not committed)
└── credentials.json   # Google credentials (not committed)
```

## Security Notes

⚠️ **Important**: The following files contain sensitive information and are NOT committed to git:

- `auth.json` - Malt session authentication
- `credentials.json` - Google Cloud service account credentials
- `.env` - Environment variables and API keys

These files are listed in `.gitignore` for security. Never share or commit these files.

## Troubleshooting

### "credentials.json not found"
Ensure your Google Service Account JSON key file is named `credentials.json` and placed in the project root.

### "SPREADSHEET_ID not set"
Add your Google Sheet ID to the `.env` file:
```env
SPREADSHEET_ID=your_id_here
```

### Browser automation fails
Ensure Playwright is properly installed:
```bash
python -m playwright install
```

### Authentication expires
If `auth.json` becomes invalid, delete it and run the scraper again to re-authenticate.

## Dependencies

- `playwright` - Browser automation
- `playwright-stealth` - Stealth plugin for Playwright
- `google-auth` - Google authentication
- `google-api-python-client` - Google Sheets API client
- `python-dotenv` - Environment variable management

## License

[Add your license information here]

## Contact

For questions or issues, please open an issue on the repository.
