#!/usr/bin/env python3
"""
Malt Analytics Scraper with Google Sheets Sync
Scrapes Malt analytics and syncs data to Google Sheets.
"""

import json
import logging
import os
import random
from datetime import datetime
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
MALT_URL = "https://www.malt.fr/dashboard/freelancer/analytics"
AUTH_FILE = "auth.json"
CREDENTIALS_FILE = "credentials.json"
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "")
SHEET_NAME = "Raw_Data"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def load_auth_storage() -> Optional[Dict[str, Any]]:
    """Load Playwright auth storage from auth.json."""
    try:
        if os.path.exists(AUTH_FILE):
            with open(AUTH_FILE, "r") as f:
                return json.load(f)
        logger.warning(f"{AUTH_FILE} not found. Starting without saved session.")
        return None
    except Exception as e:
        logger.error(f"Error loading auth storage: {e}")
        return None


def load_google_credentials() -> Credentials:
    """Load Google Service Account credentials."""
    try:
        if not os.path.exists(CREDENTIALS_FILE):
            raise FileNotFoundError(
                f"{CREDENTIALS_FILE} not found. Please ensure the file exists."
            )
        
        credentials = Credentials.from_service_account_file(
            CREDENTIALS_FILE, scopes=SCOPES
        )
        logger.info("Google credentials loaded successfully.")
        return credentials
    except Exception as e:
        logger.error(f"Error loading Google credentials: {e}")
        raise


def clean_appearances(text: str) -> int:
    """
    Clean appearances text and convert to integer.
    Examples: '1.2k' -> 1200, '5' -> 5
    """
    try:
        text = text.strip().lower()
        
        # Handle 'k' suffix (thousands)
        if 'k' in text:
            # Extract number and multiply by 1000
            number = float(text.replace('k', ''))
            return int(number * 1000)
        
        # Try direct conversion
        return int(float(text))
    except Exception as e:
        logger.warning(f"Could not clean appearances text '{text}': {e}")
        return 0


def clean_rank(text: str) -> int:
    """
    Clean rank text and convert to integer.
    Examples: '#1' -> 1, '42' -> 42
    """
    try:
        text = text.strip().replace('#', '')
        return int(text)
    except Exception as e:
        logger.warning(f"Could not clean rank text '{text}': {e}")
        return 0


def expand_keyword_table(page: Any) -> int:
    """
    Expand the keyword table by clicking 'Voir plus de résultats' button.
    Returns the number of expansions performed.
    """
    expansion_count = 0
    max_attempts = 100  # Prevent infinite loops
    
    try:
        while expansion_count < max_attempts:
            try:
                # Look for the specific button with text "Voir plus de résultats"
                voir_plus_button = page.locator('button:has-text("Voir plus de résultats")').first
                
                # Check if button exists and is visible and enabled
                if not voir_plus_button.is_visible():
                    logger.info("'Voir plus de résultats' button not found or not visible. All data loaded.")
                    break
                
                # Click the button with small delay
                voir_plus_button.click()
                
                # Wait for new entries to load
                page.wait_for_timeout(2000)
                
                expansion_count += 1
                logger.info(f"Expansion #{expansion_count} completed.")
                
            except Exception as e:
                logger.debug(f"Error during expansion iteration: {e}")
                break
    
    except Exception as e:
        logger.error(f"Error in expand_keyword_table: {e}")
    
    return expansion_count


def scrape_keyword_data(page: Any) -> List[Dict[str, Any]]:
    """
    Extract keyword data from .keywords__row elements.
    Returns list of dicts with: keyword, appearances, rank
    """
    keywords_data: List[Dict[str, Any]] = []
    
    try:
        # Find all rows with class .keywords__row
        rows = page.locator(".keywords__row").all()
        logger.info(f"Found {len(rows)} keyword rows.")
        
        for row in rows:
            try:
                # Get all span elements inside the row
                spans = row.locator("span").all()
                
                # Need at least 3 spans: keyword, appearances, rank
                if len(spans) < 3:
                    logger.debug(f"Row has {len(spans)} spans, skipping (need at least 3).")
                    continue
                
                # Extract text from spans and clean whitespace
                # Order: span[0]=keyword, span[1]=appearances, span[2]=rank
                keyword = spans[0].text_content().strip()
                appearances_text = spans[1].text_content().strip()
                rank_text = spans[2].text_content().strip()
                
                # Skip if keyword is empty
                if not keyword:
                    continue
                
                # Convert to proper types
                appearances = clean_appearances(appearances_text)
                rank = clean_rank(rank_text)
                
                keywords_data.append({
                    "keyword": keyword,
                    "appearances": appearances,
                    "rank": rank
                })
                
            except Exception as e:
                logger.debug(f"Error extracting row data: {e}")
                continue
        
        logger.info(f"Successfully scraped {len(keywords_data)} keywords.")
        return keywords_data
        
    except Exception as e:
        logger.error(f"Error scraping keyword data: {e}")
        return []


def sync_to_google_sheets(keywords_data: List[Dict[str, Any]]) -> bool:
    """
    Sync scraped data to Google Sheets.
    Appends rows with format: [Date, Keyword, Appearances, Rank]
    """
    try:
        if not SPREADSHEET_ID:
            logger.error("SPREADSHEET_ID environment variable not set.")
            return False
        
        if not keywords_data:
            logger.warning("No data to sync to Google Sheets.")
            return False
        
        # Log masked spreadsheet ID for verification
        masked_id = SPREADSHEET_ID[:10] + "..." + SPREADSHEET_ID[-10:] if len(SPREADSHEET_ID) > 20 else SPREADSHEET_ID
        logger.info(f"Using Spreadsheet ID: {masked_id}")
        
        credentials = load_google_credentials()
        service = build("sheets", "v4", credentials=credentials)
        
        # Verify sheet exists or create it
        try:
            sheet_metadata = service.spreadsheets().get(
                spreadsheetId=SPREADSHEET_ID,
                fields="sheets.properties"
            ).execute()
            
            sheets = sheet_metadata.get("sheets", [])
            sheet_names = [sheet["properties"]["title"] for sheet in sheets]
            
            logger.info(f"Available sheets: {sheet_names}")
            
            if SHEET_NAME not in sheet_names:
                logger.warning(f"Sheet '{SHEET_NAME}' not found. Available sheets: {sheet_names}")
                logger.error(f"Please create a sheet named '{SHEET_NAME}' in your Google Sheet.")
                return False
            
            logger.info(f"Sheet '{SHEET_NAME}' verified and exists.")
            
        except Exception as e:
            logger.error(f"Error verifying sheet: {e}")
            logger.error(f"Make sure SPREADSHEET_ID is correct and you have access to the spreadsheet.")
            return False
        
        # Get current date
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Prepare rows for batch append
        # Format: [date, keyword, appearances, rank]
        rows: List[List[Any]] = []
        for item in keywords_data:
            row = [
                today,
                item["keyword"],
                item["appearances"],
                item["rank"]
            ]
            rows.append(row)
        
        logger.info(f"Prepared {len(rows)} rows for batch append.")
        logger.debug(f"Sample row: {rows[0] if rows else 'No rows'}")
        
        # Batch append to Google Sheets
        body: Dict[str, List[List[Any]]] = {
            "values": rows
        }
        
        try:
            result = service.spreadsheets().values().append(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{SHEET_NAME}!A:D",
                valueInputOption="USER_ENTERED",
                body=body
            ).execute()
            
            updates = result.get("updates", {})
            updated_rows = updates.get("updatedRows", 0)
            
            logger.info(
                f"Successfully synced {updated_rows} rows to Google Sheets "
                f"(Sheet: {SHEET_NAME})"
            )
            return True
            
        except Exception as append_error:
            # Provide detailed error information
            error_message = str(append_error)
            logger.error(f"Error appending rows to Google Sheets: {error_message}")
            
            # Check for specific error types
            if "403" in error_message:
                logger.error("Permission denied (403). Verify you have edit access to the spreadsheet.")
            elif "404" in error_message:
                logger.error("Spreadsheet not found (404). Verify SPREADSHEET_ID is correct.")
            elif "400" in error_message:
                logger.error("Bad request (400). Check your data format and range.")
            
            return False
        
    except Exception as e:
        logger.error(f"Fatal error in sync_to_google_sheets: {e}", exc_info=True)
        return False


def main() -> int:
    """Main scraper execution."""
    expansion_count = 0
    scraped_count = 0
    
    try:
        # Load auth storage
        auth_storage = load_auth_storage()
        
        with sync_playwright() as p:
            # Launch browser with headless mode
            browser = p.chromium.launch(headless=False)
            
            # Create context with auth storage
            context_kwargs: Dict[str, Any] = {
                "locale": "en-US",
            }
            
            if auth_storage:
                context_kwargs["storage_state"] = auth_storage
            
            context = browser.new_context(**context_kwargs)
            page = context.new_page()
            
            # Apply stealth mode using the correct class method
            Stealth().apply_stealth_sync(page)
            
            # Navigate to Malt analytics
            logger.info(f"Navigating to {MALT_URL}")
            page.goto(MALT_URL, wait_until="domcontentloaded")
            page.wait_for_selector(".keywords__row", timeout=15000)

            # Expand the keyword table
            logger.info("Starting expansion loop...")
            expansion_count = expand_keyword_table(page)
            
            # Scrape keyword data
            logger.info("Extracting keyword data...")
            keywords_data = scrape_keyword_data(page)
            scraped_count = len(keywords_data)
            
            # Close browser
            browser.close()
        
        # Sync to Google Sheets
        logger.info("Syncing data to Google Sheets...")
        sync_successful = sync_to_google_sheets(keywords_data)
        
        # Print final summary
        print(f"\n{'='*60}")
        print(f"Scraping Complete!")
        print(f"{'='*60}")
        print(f"Expanded {expansion_count} times. Scraped {scraped_count} keywords.")
        print(f"Google Sheets Sync: {'✓ Success' if sync_successful else '✗ Failed'}")
        print(f"{'='*60}\n")
        
        return 0 if sync_successful else 1
        
    except Exception as e:
        logger.error(f"Fatal error in main execution: {e}", exc_info=True)
        print(f"\nError: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
