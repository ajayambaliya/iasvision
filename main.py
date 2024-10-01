import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from deep_translator import GoogleTranslator
import os
from googleapiclient.discovery import build
from google.oauth2 import service_account

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

# Dictionary to store the original content for later writing
original_content = {}

# Function to scrape content from the provided URL and translate to Gujarati
def scrap_and_add_content_to_docs(url):
    print(f"Scraping: {url}")
    page_response = requests.get(url)
    page_soup = BeautifulSoup(page_response.content, 'html.parser')

    content_area = page_soup.find('div', class_="flex flex-col w-full mt-6 lg:mt-0")
    doc_requests = []  # Requests to send to the Google Docs API

    if content_area:
        title = content_area.find('h1').get_text()
        translated_title = translator.translate(title)
        
        # Add the translated title to Google Docs
        doc_requests.append({
            'insertText': {
                'location': {'index': 1},
                'text': f"\n{translated_title}\n"
            }
        })

        # Store the original title for later use in English content
        original_content[url] = {"title": title, "content": []}

        # Find article content under the <div id="article-content">
        article_content = content_area.find('div', id='article-content')
        if article_content:
            for element in article_content.find_all(recursive=False):
                if element.name == 'p':
                    paragraph_text = element.get_text()
                    translated_paragraph = translator.translate(paragraph_text)
                    
                    # Add translated paragraph to Google Docs
                    doc_requests.append({
                        'insertText': {
                            'location': {'index': 1},
                            'text': f"\n{translated_paragraph}\n"
                        }
                    })
                    # Store the original paragraph for English content
                    original_content[url]["content"].append({"type": "p", "text": paragraph_text})

                elif element.name == 'h2':
                    sub_heading_text = element.get_text()
                    translated_sub_heading = translator.translate(sub_heading_text)
                    
                    # Add translated sub-heading to Google Docs
                    doc_requests.append({
                        'insertText': {
                            'location': {'index': 1},
                            'text': f"\n{translated_sub_heading}\n"
                        }
                    })
                    # Store the original sub-heading for English content
                    original_content[url]["content"].append({"type": "h2", "text": sub_heading_text})

                elif element.name == 'ul':  # For unordered lists
                    list_items = []
                    for li in element.find_all('li'):
                        list_item_text = li.get_text()
                        translated_list_item = translator.translate(list_item_text)

                        # Add translated list item to Google Docs
                        doc_requests.append({
                            'insertText': {
                                'location': {'index': 1},
                                'text': f"- {translated_list_item}\n"
                            }
                        })
                        # Store original list item for English content
                        list_items.append(list_item_text)
                    original_content[url]["content"].append({"type": "ul", "items": list_items})

                elif element.name == 'ol':  # For ordered lists
                    list_items = []
                    for li in element.find_all('li'):
                        list_item_text = li.get_text()
                        translated_list_item = translator.translate(list_item_text)

                        # Add translated list item to Google Docs
                        doc_requests.append({
                            'insertText': {
                                'location': {'index': 1},
                                'text': f"1. {translated_list_item}\n"
                            }
                        })
                        # Store original list item for English content
                        list_items.append(list_item_text)
                    original_content[url]["content"].append({"type": "ol", "items": list_items})

    # Add the translated content to Google Docs
    docs_service.documents().batchUpdate(documentId=document_id, body={'requests': doc_requests}).execute()

# Iterate over unique URLs and scrape content
for url in unique_urls:
    scrap_and_add_content_to_docs(url)

# Add a heading for the original English content in Google Docs
doc_requests = []
doc_requests.append({
    'insertText': {
        'location': {'index': 1},
        'text': "\nOriginal Content in English\n"
    }
})
docs_service.documents().batchUpdate(documentId=document_id, body={'requests': doc_requests}).execute()

# Write original English content to Google Docs
for url, content_data in original_content.items():
    # Add original title
    doc_requests.append({
        'insertText': {
            'location': {'index': 1},
            'text': f"\n{content_data['title']}\n"
        }
    })

    # Add the original content (paragraphs, headings, lists, etc.)
    for content_item in content_data["content"]:
        if content_item["type"] == "p":
            doc_requests.append({
                'insertText': {
                    'location': {'index': 1},
                    'text': f"\n{content_item['text']}\n"
                }
            })
        elif content_item["type"] == "h2":
            doc_requests.append({
                'insertText': {
                    'location': {'index': 1},
                    'text': f"\n{content_item['text']}\n"
                }
            })
        elif content_item["type"] == "ul":
            for item in content_item["items"]:
                doc_requests.append({
                    'insertText': {
                        'location': {'index': 1},
                        'text': f"- {item}\n"
                    }
                })
        elif content_item["type"] == "ol":
            for item in content_item["items"]:
                doc_requests.append({
                    'insertText': {
                        'location': {'index': 1},
                        'text': f"1. {item}\n"
                    }
                })

# Add the original content to Google Docs
docs_service.documents().batchUpdate(documentId=document_id, body={'requests': doc_requests}).execute()

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
