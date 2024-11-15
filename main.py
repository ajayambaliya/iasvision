import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from deep_translator import GoogleTranslator
import os
import time
from urllib.parse import quote
import logging
import html
import re

# ------------------------ Configuration ------------------------

# Telegram bot credentials and channel/chat IDs from environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
GUJARATI_CHAT_ID = os.getenv('GUJARATI_CHAT_ID')
ENGLISH_CHAT_ID = os.getenv('ENGLISH_CHAT_ID')
GUJARATI_CHANNEL_ID = os.getenv('GUJARATI_CHANNEL_ID')
ENGLISH_CHANNEL_ID = os.getenv('ENGLISH_CHANNEL_ID')

# Validate that all necessary environment variables are set
required_env_vars = {
    'BOT_TOKEN': BOT_TOKEN,
    'GUJARATI_CHAT_ID': GUJARATI_CHAT_ID,
    'ENGLISH_CHAT_ID': ENGLISH_CHAT_ID,
    'GUJARATI_CHANNEL_ID': GUJARATI_CHANNEL_ID,
    'ENGLISH_CHANNEL_ID': ENGLISH_CHANNEL_ID
}

missing_vars = [var for var, value in required_env_vars.items() if not value]
if missing_vars:
    logging.critical(f"Missing environment variables: {', '.join(missing_vars)}. Please set them before running the script.")
    exit(1)

# Channel promotional message
CHANNEL_PROMO = """
╔════════════════════════════════════════╗
    📱 Follow Us For More
• Daily Current Affairs Gujarati: @CurrentAdda
• For 48000+ Que Quiz and Daily Current Affairs Quiz Use Our bot @GovPrepBuddy_bot
• Share & Support: Forward to Friends
╚════════════════════════════════════════╝"""

# Formatting decorators
TITLE_DECORATOR = "🌟━━━━━━━━━━━━━━━━━━━━━━━━━🌟"
TITLE_DECORATOR_END = "🌟━━━━━━━━━━━━━━━━━━━━━━━━━━🌟"
SECTION_DIVIDER = "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"
TOPIC_DECORATOR = "📍"

# Logging configuration
logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for detailed logs during debugging
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

# Translator setup
translator = GoogleTranslator(source='auto', target='gu')

# ------------------------ Helper Functions ------------------------

def clean_text_html(text):
    """
    Cleans and escapes text for HTML parse mode.
    """
    if not text:
        return ""
    
    # Normalize whitespace
    text = ' '.join(text.split())
    
    # Escape HTML special characters
    text = html.escape(text)
    
    return text.strip()

def format_title_html(title):
    """Format title with proper escaping and HTML formatting."""
    cleaned_title = clean_text_html(title)
    formatted_text = f"""
{TITLE_DECORATOR}
   <b>{cleaned_title}</b>
{TITLE_DECORATOR_END}

"""
    return formatted_text

def format_subheading_html(subheading):
    """Format subheading with proper escaping and HTML formatting."""
    cleaned_subheading = clean_text_html(subheading)
    formatted_text = f"""
{TOPIC_DECORATOR} <b>{cleaned_subheading}</b>
{SECTION_DIVIDER}

"""
    return formatted_text

def format_paragraph_html(paragraph):
    """Format paragraph with proper escaping and HTML formatting."""
    cleaned_paragraph = clean_text_html(paragraph)
    return f"{cleaned_paragraph}\n\n"

def format_list_item_html(item):
    """Format list item with proper escaping and HTML formatting."""
    cleaned_item = clean_text_html(item)
    return f"• {cleaned_item}\n"

def add_timestamp_html():
    """Add formatted timestamp."""
    return f"\n⌚ {datetime.now().strftime('%d %B %Y, %I:%M %p')}\n"

def get_message_link(channel_username, message_id):
    """Generate message link with proper escaping."""
    channel_username = clean_text_html(channel_username)
    return f"https://t.me/{channel_username}/{message_id}"

def send_message_to_telegram_html(text, chat_id, retry_count=3):
    """
    Enhanced Telegram message sender using HTML parse mode.
    """
    max_length = 4096

    # Log the message content for debugging
    logging.debug(f"Message content to send: {text}")

    # Split long messages
    if len(text) > max_length:
        parts = [text[i:i + max_length] for i in range(0, len(text), max_length)]
        message_id = None
        for part in parts:
            message_id = send_message_to_telegram_html(part, chat_id, retry_count)
            time.sleep(1)
        return message_id

    for attempt in range(retry_count):
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True
            }
            
            response = requests.post(url, data=payload, timeout=30)
            
            if response.status_code == 200:
                return response.json()['result']['message_id']
            
            logging.warning(f"Attempt {attempt + 1} failed: {response.status_code}, {response.text}")
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 5))
                logging.info(f"Rate limited. Retrying after {retry_after} seconds.")
                time.sleep(retry_after)
                continue
            
            # Exponential backoff for other errors
            if attempt < retry_count - 1:
                backoff_time = 2 ** attempt
                logging.info(f"Retrying after {backoff_time} seconds.")
                time.sleep(backoff_time)
                
        except Exception as e:
            logging.error(f"Error on attempt {attempt + 1}: {str(e)}")
            if attempt < retry_count - 1:
                backoff_time = 2 ** attempt
                logging.info(f"Retrying after {backoff_time} seconds.")
                time.sleep(backoff_time)
    
    logging.error("Failed to send message after multiple attempts.")
    return None

def process_content_html(element, translate=False, message_content=""):
    """Enhanced content processor with better handling of special characters using HTML."""
    try:
        text = element.get_text()
        if not text:
            return message_content

        # Handle links separately if present
        links = element.find_all('a')
        for link in links:
            href = link.get('href', '')
            link_text = link.get_text()
            # Replace link text with hyperlink
            if href and link_text:
                escaped_href = clean_text_html(href)
                escaped_link_text = clean_text_html(link_text)
                hyperlink = f'<a href="{escaped_href}">{escaped_link_text}</a>'
                text = text.replace(link_text, hyperlink)

        text = clean_text_html(text)
        
        try:
            processed_text = translator.translate(text) if translate else text
        except Exception as e:
            logging.error(f"Translation error: {str(e)}")
            processed_text = text

        if element.name == 'h2':
            message_content += format_subheading_html(processed_text)
        elif element.name == 'p':
            if processed_text not in message_content:
                message_content += format_paragraph_html(processed_text)
        elif element.name in ['ul', 'ol']:
            for li in element.find_all('li'):
                li_text = li.get_text()
                # Handle links within list items
                li_links = li.find_all('a')
                for link in li_links:
                    href = link.get('href', '')
                    link_text = link.get_text()
                    if href and link_text:
                        escaped_href = clean_text_html(href)
                        escaped_link_text = clean_text_html(link_text)
                        hyperlink = f'<a href="{escaped_href}">{escaped_link_text}</a>'
                        li_text = li_text.replace(link_text, hyperlink)
                cleaned_li_text = clean_text_html(li_text)
                try:
                    processed_li = translator.translate(cleaned_li_text) if translate else cleaned_li_text
                except Exception as e:
                    logging.error(f"Translation error in list item: {str(e)}")
                    processed_li = cleaned_li_text
                if processed_li not in message_content:
                    message_content += format_list_item_html(processed_li)
        
        return message_content
    except Exception as e:
        logging.error(f"Error processing content: {str(e)}")
        return message_content

def scrape_and_send_to_telegram(url):
    """Main scraping function with improved content detection and error handling."""
    try:
        logging.info(f"Processing URL: {url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        page_response = requests.get(url, headers=headers, timeout=30)
        if page_response.status_code != 200:
            logging.error(f"Failed to fetch URL: {url}, Status: {page_response.status_code}")
            return
        
        page_soup = BeautifulSoup(page_response.content, 'html.parser')
        
        # Try multiple selectors to find content area
        content_area = (
            page_soup.find('div', class_="flex flex-col w-full mt-6 lg:mt-0") or
            page_soup.find('div', class_="article-content") or
            page_soup.find('article') or
            page_soup.find('main')
        )
        
        if not content_area:
            logging.error(f"No content area found for URL: {url}")
            return
        
        # Find title - try multiple approaches
        title_element = (
            content_area.find('h1') or
            page_soup.find('h1') or
            page_soup.find('title')
        )
        
        if not title_element:
            logging.error(f"No title found for URL: {url}")
            return
            
        title = title_element.get_text()
        
        # Process English content
        english_content = format_title_html(title)
        
        # Try multiple selectors for article content
        article_content = (
            content_area.find('div', id='article-content') or
            content_area.find('div', class_='article-content') or
            content_area.find('div', class_='content') or
            content_area
        )
        
        if article_content:
            # Get all content elements
            content_elements = article_content.find_all(['h2', 'p', 'ul', 'ol'])
            
            for element in content_elements:
                if element.parent and 'header' in element.parent.get('class', []):
                    continue  # Skip header elements
                english_content = process_content_html(element, translate=False, message_content=english_content)
        
        # Add timestamp and promotional content
        english_content += add_timestamp_html()
        english_content += CHANNEL_PROMO.strip() + "\n"
        
        # Send English content
        english_message_id = send_message_to_telegram_html(english_content, ENGLISH_CHAT_ID)
        if not english_message_id:
            logging.error("Failed to send English message")
            return
        
        # Process Gujarati content
        try:
            translated_title = translator.translate(title)
        except Exception as e:
            logging.error(f"Title translation failed: {str(e)}")
            translated_title = title
            
        gujarati_content = format_title_html(translated_title)
        
        if article_content:
            for element in content_elements:
                if element.parent and 'header' in element.parent.get('class', []):
                    continue
                gujarati_content = process_content_html(element, translate=True, message_content=gujarati_content)
        
        # Add English article link and format
        english_message_link = get_message_link(ENGLISH_CHANNEL_ID, english_message_id)
        gujarati_content += f'\n📱 <b>For Reading This Article in English :</b> <a href="{english_message_link}">Click Here</a>\n'
        
        # Add timestamp and promotional content
        gujarati_content += add_timestamp_html()
        gujarati_content += CHANNEL_PROMO.strip() + "\n"
        
        # Send Gujarati content
        send_message_to_telegram_html(gujarati_content, GUJARATI_CHAT_ID)
        time.sleep(2)  # Rate limiting
        
    except Exception as e:
        logging.error(f"Error processing URL {url}: {str(e)}")

def main():
    """Main function with improved error handling and logging."""
    base_url = "https://visionias.in/current-affairs/"
    try:
        logging.info("Fetching base URL")
        response = requests.get(base_url, timeout=30)
        logging.info(f"Base URL response: {response.status_code}")
        
        if response.status_code != 200:
            logging.error(f"Failed to fetch base URL: {response.status_code}")
            return
        
        soup = BeautifulSoup(response.content, 'html.parser')
        previous_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        logging.info(f"Looking for articles from: {previous_date}")
        
        anchors = soup.find_all('a', href=lambda href: href and previous_date in href)
        logging.info(f"Found {len(anchors)} articles")
        
        unique_urls = {
            base_url.rstrip('/') + '/' + a['href'].replace('/current-affairs/', '', 1)
            for a in anchors if a['href'].startswith('/current-affairs/')
        }
        
        for url in unique_urls:
            try:
                scrape_and_send_to_telegram(url)
            except Exception as e:
                logging.error(f"Error processing URL {url}: {str(e)}")
                continue
            
    except Exception as e:
        logging.error(f"Error in main function: {str(e)}")

if __name__ == "__main__":
    main()
