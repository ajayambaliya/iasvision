import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from docx import Document
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
import os
from deep_translator import GoogleTranslator
import weasyprint
import shutil

# Load environment variables for bot token and chat ID
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

# Define base URL
base_url = "https://visionias.in/current-affairs/"

# Get the previous date in 'yyyy-mm-dd' format
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
        # Remove '/current-affairs/' from the href to get the correct URL format
        correct_href = href.replace('/current-affairs/', '', 1)
        full_url = base_url.rstrip('/') + '/' + correct_href
        unique_urls.add(full_url)  # Adding to set ensures no duplicates

# Initialize a Word Document
doc = Document()

# Create an instance of the GoogleTranslator to translate to Gujarati
translator = GoogleTranslator(source='auto', target='gu')

# Store content in HTML format for conversion
html_content = "<html><head><style>body { font-family: 'Noto Sans', sans-serif; }</style></head><body>"

# Function to scrape content from the provided URL and translate to Gujarati
def scrap_and_create_doc(url):
    global html_content
    print(f"Scraping: {url}")
    page_response = requests.get(url)
    page_soup = BeautifulSoup(page_response.content, 'html.parser')

    # Find the specific content area div
    content_area = page_soup.find('div', class_="flex flex-col w-full mt-6 lg:mt-0")

    if content_area:
        # Extract the title from the <h1> tag
        title = content_area.find('h1').get_text()
        translated_title = translator.translate(title)  # Translate the title to Gujarati
        
        # Add to DOCX
        doc.add_heading(translated_title, 0).alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        
        # Add to HTML content
        html_content += f"<h1 style='text-align: center;'>{translated_title}</h1>"

        # Find article content under the <div id="article-content">
        article_content = content_area.find('div', id='article-content')

        if article_content:
            # Loop through each child element in the article content
            for element in article_content.find_all(recursive=False):
                if element.name == 'p':  # For paragraphs
                    paragraph_text = element.get_text()
                    translated_paragraph = translator.translate(paragraph_text)  # Translate paragraph
                    
                    # Add to DOCX
                    paragraph = doc.add_paragraph(translated_paragraph)
                    paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
                    
                    # Add to HTML content
                    html_content += f"<p>{translated_paragraph}</p>"

                elif element.name == 'h2':  # For sub-headings
                    sub_heading_text = element.get_text()
                    translated_sub_heading = translator.translate(sub_heading_text)  # Translate sub-heading
                    
                    # Add to DOCX
                    doc.add_heading(translated_sub_heading, level=2)
                    
                    # Add to HTML content
                    html_content += f"<h2>{translated_sub_heading}</h2>"

                elif element.name == 'ul':  # For lists
                    html_content += "<ul>"
                    for li in element.find_all('li'):
                        list_item_text = li.get_text()
                        translated_list_item = translator.translate(list_item_text)  # Translate list item
                        
                        # Add to DOCX
                        doc.add_paragraph(translated_list_item, style='List Bullet')
                        
                        # Add to HTML content
                        html_content += f"<li>{translated_list_item}</li>"
                    html_content += "</ul>"

                elif element.name == 'ol':  # For ordered lists
                    html_content += "<ol>"
                    for li in element.find_all('li'):
                        list_item_text = li.get_text()
                        translated_list_item = translator.translate(list_item_text)  # Translate list item
                        
                        # Add to DOCX
                        doc.add_paragraph(translated_list_item, style='List Number')
                        
                        # Add to HTML content
                        html_content += f"<li>{translated_list_item}</li>"
                    html_content += "</ol>"

# Iterate over unique URLs and scrape content
for url in unique_urls:
    scrap_and_create_doc(url)

# Add a heading for the original content in English
doc.add_page_break()
doc.add_heading('Original Content in English', level=1)

html_content += "<h1 style='text-align: center;'>Original Content in English</h1>"

# Save the DOCX file
file_name = f"visionias_current_affairs_{previous_date}.docx"
doc.save(file_name)
print(f"Document saved as {file_name}")

# Convert HTML content to PDF using WeasyPrint
html_content += "</body></html>"
pdf_file_name = f"visionias_current_affairs_{previous_date}.pdf"

# Write the HTML to a temporary file for WeasyPrint conversion
with open("temp.html", "w", encoding='utf-8') as html_file:
    html_file.write(html_content)

# Use WeasyPrint to convert HTML to PDF
weasyprint.HTML("temp.html").write_pdf(pdf_file_name)

# Remove the temporary HTML file
os.remove("temp.html")
print(f"PDF saved as {pdf_file_name}")

# Send the PDF file to Telegram
def send_file_to_telegram(pdf_file):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    with open(pdf_file, 'rb') as file:
        response = requests.post(url, data={'chat_id': CHAT_ID}, files={'document': file})
    
    if response.status_code == 200:
        print(f"PDF file sent to Telegram channel successfully.")
    else:
        print(f"Failed to send PDF file. Status code: {response.status_code}, Response: {response.text}")

# Send the generated PDF to Telegram
send_file_to_telegram(pdf_file_name)

# Optionally, cleanup the local files
os.remove(file_name)
os.remove(pdf_file_name)
