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

# Function to batch updates and send them to Google Docs
def batch_update_to_docs(requests_batch):
    """Helper function to batch update Google Docs to avoid hitting rate limits."""
    if requests_batch:
        try:
            docs_service.documents().batchUpdate(documentId=document_id, body={'requests': requests_batch}).execute()
        except Exception as e:
            print(f"Error while updating Google Docs: {e}")
        # Sleep briefly to avoid hitting the rate limit
        time.sleep(1)

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
        
        # Add Gujarati Title (Heading 1)
        requests_batch.append({
            'insertText': {
                'location': {'index': 1},
                'text': f"{translated_title}\n"
            }
        })
        requests_batch.append({
            'updateParagraphStyle': {
                'range': {'startIndex': 1, 'endIndex': 1 + len(translated_title)},
                'paragraphStyle': {'namedStyleType': 'HEADING_1'},
                'fields': 'namedStyleType'
            }
        })

        # Add English Title (Heading 1)
        requests_batch.append({
            'insertText': {
                'location': {'index': 1},
                'text': f"{title}\n"
            }
        })
        requests_batch.append({
            'updateParagraphStyle': {
                'range': {'startIndex': 1 + len(translated_title), 'endIndex': 1 + len(translated_title) + len(title)},
                'paragraphStyle': {'namedStyleType': 'HEADING_1'},
                'fields': 'namedStyleType'
            }
        })

        # Find article content under the <div id="article-content">
        article_content = content_area.find('div', id='article-content')
        if article_content:
            for element in article_content.find_all(recursive=False):
                if element.name == 'p':
                    paragraph_text = element.get_text()
                    translated_paragraph = translator.translate(paragraph_text)

                    # Add translated Gujarati paragraph
                    requests_batch.append({
                        'insertText': {
                            'location': {'index': 1},
                            'text': f"{translated_paragraph}\n"
                        }
                    })

                    # Add original English paragraph
                    requests_batch.append({
                        'insertText': {
                            'location': {'index': 1},
                            'text': f"{paragraph_text}\n"
                        }
                    })

                elif element.name == 'h2':
                    sub_heading_text = element.get_text()
                    translated_sub_heading = translator.translate(sub_heading_text)

                    # Add translated Gujarati sub-heading
                    requests_batch.append({
                        'insertText': {
                            'location': {'index': 1},
                            'text': f"{translated_sub_heading}\n"
                        }
                    })

                    # Add original English sub-heading
                    requests_batch.append({
                        'insertText': {
                            'location': {'index': 1},
                            'text': f"{sub_heading_text}\n"
                        }
                    })

                elif element.name == 'ul':
                    for li in element.find_all('li'):
                        list_item_text = li.get_text()
                        translated_list_item = translator.translate(list_item_text)

                        # Add translated Gujarati list item
                        requests_batch.append({
                            'insertText': {
                                'location': {'index': 1},
                                'text': f"• {translated_list_item}\n"
                            }
                        })

                        # Add original English list item
                        requests_batch.append({
                            'insertText': {
                                'location': {'index': 1},
                                'text': f"• {list_item_text}\n"
                            }
                        })

                elif element.name == 'ol':
                    for index, li in enumerate(element.find_all('li'), 1):
                        list_item_text = li.get_text()
                        translated_list_item = translator.translate(list_item_text)

                        # Add translated Gujarati ordered list item
                        requests_batch.append({
                            'insertText': {
                                'location': {'index': 1},
                                'text': f"{index}. {translated_list_item}\n"
                            }
                        })

                        # Add original English ordered list item
                        requests_batch.append({
                            'insertText': {
                                'location': {'index': 1},
                                'text': f"{index}. {list_item_text}\n"
                            }
                        })

        # Send all collected updates for this URL in a single batch request
        batch_update_to_docs(requests_batch)

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
