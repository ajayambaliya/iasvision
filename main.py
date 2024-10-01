import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from deep_translator import GoogleTranslator
import os
from googleapiclient.discovery import build
from google.oauth2 import service_account
import time

# Telegram bot credentials
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

# Google API setup
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents']
SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

# Set up Google Docs and Drive API
credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
docs_service = build('docs', 'v1', credentials=credentials)
drive_service = build('drive', 'v3', credentials=credentials)

# Define base URL
base_url = "https://visionias.in/current-affairs/"
previous_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

# Send GET request to the base URL
response = requests.get(base_url)
soup = BeautifulSoup(response.content, 'html.parser')

# Find all anchor tags with href containing the previous date
anchors = soup.find_all('a', href=lambda href: href and previous_date in href)

# Create a set to store unique URLs (set ensures uniqueness)
unique_urls = set()
for a in anchors:
    href = a['href']
    if href.startswith('/current-affairs/'):
        correct_href = href.replace('/current-affairs/', '', 1)
        full_url = base_url.rstrip('/') + '/' + correct_href
        unique_urls.add(full_url)

# Create a Google Docs document
doc_title = f"VisionIAS Current Affairs {previous_date}"
document = docs_service.documents().create(body={'title': doc_title}).execute()
document_id = document.get('documentId')

# Google Translator
translator = GoogleTranslator(source='auto', target='gu')

# Function to format and add content to Google Docs
def format_and_add_to_docs(requests_batch):
    """Helper function to format and send batched content to Google Docs."""
    if requests_batch:
        try:
            docs_service.documents().batchUpdate(documentId=document_id, body={'requests': requests_batch}).execute()
        except Exception as e:
            print(f"Error while updating Google Docs: {e}")
        # Sleep briefly to avoid hitting the rate limit
        time.sleep(1)

def create_section_separator(requests_batch):
    """Helper function to add a separator between sections."""
    requests_batch.append({
        'insertText': {
            'location': {'index': 1},
            'text': "\n---\n\n"
        }
    })

def add_title(requests_batch, title_text):
    """Add a title (translated and original) to the document."""
    requests_batch.append({
        'insertText': {
            'location': {'index': 1},
            'text': f"{title_text}\n"
        }
    })
    requests_batch.append({
        'updateParagraphStyle': {
            'range': {'startIndex': 1, 'endIndex': 1 + len(title_text)},
            'paragraphStyle': {'namedStyleType': 'HEADING_1'},
            'fields': 'namedStyleType'
        }
    })

def add_subheading(requests_batch, subheading_text):
    """Add a subheading (translated and original) to the document."""
    requests_batch.append({
        'insertText': {
            'location': {'index': 1},
            'text': f"{subheading_text}\n"
        }
    })
    requests_batch.append({
        'updateParagraphStyle': {
            'range': {'startIndex': 1, 'endIndex': 1 + len(subheading_text)},
            'paragraphStyle': {'namedStyleType': 'HEADING_2'},
            'fields': 'namedStyleType'
        }
    })

def add_paragraph(requests_batch, paragraph_text):
    """Add a regular paragraph to the document."""
    requests_batch.append({
        'insertText': {
            'location': {'index': 1},
            'text': f"{paragraph_text}\n"
        }
    })

def add_list_item(requests_batch, list_item_text):
    """Add a list item to the document."""
    requests_batch.append({
        'insertText': {
            'location': {'index': 1},
            'text': f"• {list_item_text}\n"
        }
    })

# Function to scrape content from URL and add to Google Docs
def scrap_and_add_content_to_docs(url):
    print(f"Scraping: {url}")
    page_response = requests.get(url)
    page_soup = BeautifulSoup(page_response.content, 'html.parser')

    content_area = page_soup.find('div', class_="flex flex-col w-full mt-6 lg:mt-0")

    requests_batch = []  # Collect updates here before sending
    if content_area:
        title = content_area.find('h1').get_text()
        translated_title = translator.translate(title)
        
        # Add Title (both Gujarati and English)
        add_title(requests_batch, translated_title)
        add_title(requests_batch, title)

        # Find article content under the <div id="article-content">
        article_content = content_area.find('div', id='article-content')
        if article_content:
            for element in article_content.find_all(recursive=False):
                if element.name == 'p':
                    paragraph_text = element.get_text()
                    translated_paragraph = translator.translate(paragraph_text)

                    # Add paragraphs (Gujarati and English)
                    add_paragraph(requests_batch, translated_paragraph)
                    add_paragraph(requests_batch, paragraph_text)

                elif element.name == 'h2':
                    sub_heading_text = element.get_text()
                    translated_sub_heading = translator.translate(sub_heading_text)

                    # Add subheadings (Gujarati and English)
                    add_subheading(requests_batch, translated_sub_heading)
                    add_subheading(requests_batch, sub_heading_text)

                elif element.name == 'ul':
                    # Unordered list
                    for li in element.find_all('li'):
                        list_item_text = li.get_text()
                        translated_list_item = translator.translate(list_item_text)

                        # Add list items (Gujarati and English)
                        add_list_item(requests_batch, translated_list_item)
                        add_list_item(requests_batch, list_item_text)

                elif element.name == 'ol':
                    # Ordered list
                    for index, li in enumerate(element.find_all('li'), 1):
                        list_item_text = li.get_text()
                        translated_list_item = translator.translate(list_item_text)

                        # Add ordered list items (Gujarati and English)
                        add_paragraph(requests_batch, f"{index}. {translated_list_item}")
                        add_paragraph(requests_batch, f"{index}. {list_item_text}")

        # Add a separator between each post
        create_section_separator(requests_batch)

        # Send all collected updates for this URL in a single batch request
        format_and_add_to_docs(requests_batch)

# Iterate over unique URLs and scrape content
for url in unique_urls:
    scrap_and_add_content_to_docs(url)

# Export the Google Docs document as a PDF
pdf_file_name = f"visionias_current_affairs_{previous_date}.pdf"
request = drive_service.files().export_media(fileId=document_id, mimeType='application/pdf')
with open(pdf_file_name, 'wb') as pdf_file:
    pdf_file.write(request.execute())

# Send the PDF file to Telegram
def send_file_to_telegram(pdf_file):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    with open(pdf_file, 'rb') as file:
        response = requests.post(url, data={'chat_id': CHAT_ID}, files={'document': file})
    
    if response.status_code == 200:
        print(f"PDF file sent to Telegram channel successfully.")
    else:
        print(f"Failed to send PDF file. Status code: {response.status_code}, Response: {response.text}")

send_file_to_telegram(pdf_file_name)

# Optionally, cleanup the local files
os.remove(pdf_file_name)
