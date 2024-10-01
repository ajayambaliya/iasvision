import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from deep_translator import GoogleTranslator
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
import os

# Telegram bot credentials
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

# Set up Google Translator for Gujarati
translator = GoogleTranslator(source='auto', target='gu')

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
        correct_href = href.replace('/current-affairs/', '', 1)
        full_url = base_url.rstrip('/') + '/' + correct_href
        unique_urls.add(full_url)

# Create the PDF using ReportLab
pdf_file_name = f"visionias_current_affairs_{previous_date}.pdf"
pdf = canvas.Canvas(pdf_file_name, pagesize=A4)
pdf.setFont("Helvetica", 12)
width, height = A4

# Registering custom fonts for English and Gujarati
pdfmetrics.registerFont(TTFont('NotoSans', 'NotoSans-Regular.ttf'))
pdfmetrics.registerFont(TTFont('NotoSansGujarati', 'NotoSansGujarati-Regular.ttf'))

y_position = height - inch  # Set initial Y position for drawing text

def write_section_to_pdf(title_gujarati, title_english, content_gujarati, content_english):
    global y_position
    
    if y_position < 1.5 * inch:
        pdf.showPage()  # Create a new page if content exceeds one page
        y_position = height - inch

    # Write the titles (Gujarati and English)
    pdf.setFont("NotoSansGujarati", 14)
    pdf.drawString(inch, y_position, title_gujarati)
    y_position -= 0.4 * inch

    pdf.setFont("NotoSans", 14)
    pdf.drawString(inch, y_position, title_english)
    y_position -= 0.4 * inch

    # Write the content paragraphs (Gujarati and English)
    pdf.setFont("NotoSansGujarati", 12)
    for guj_line in content_gujarati.split('\n'):
        pdf.drawString(inch, y_position, guj_line)
        y_position -= 0.3 * inch
        if y_position < 1.5 * inch:
            pdf.showPage()
            y_position = height - inch

    pdf.setFont("NotoSans", 12)
    for eng_line in content_english.split('\n'):
        pdf.drawString(inch, y_position, eng_line)
        y_position -= 0.3 * inch
        if y_position < 1.5 * inch:
            pdf.showPage()
            y_position = height - inch

# Function to scrape content and write to PDF
def scrape_and_generate_pdf(url):
    global y_position
    print(f"Scraping: {url}")
    page_response = requests.get(url)
    page_soup = BeautifulSoup(page_response.content, 'html.parser')

    # Find the specific content area div
    content_area = page_soup.find('div', class_="flex flex-col w-full mt-6 lg:mt-0")

    if content_area:
        title = content_area.find('h1').get_text()
        translated_title = translator.translate(title)

        # Find article content under the <div id="article-content">
        article_content = content_area.find('div', id='article-content')

        if article_content:
            content_english = ""
            content_gujarati = ""
            
            for element in article_content.find_all(recursive=False):
                if element.name == 'p':  # For paragraphs
                    paragraph_text = element.get_text()
                    translated_paragraph = translator.translate(paragraph_text)

                    content_english += paragraph_text + "\n"
                    content_gujarati += translated_paragraph + "\n"

                elif element.name == 'h2':  # For sub-headings
                    sub_heading_text = element.get_text()
                    translated_sub_heading = translator.translate(sub_heading_text)

                    content_english += f"\n{sub_heading_text}\n"
                    content_gujarati += f"\n{translated_sub_heading}\n"

                elif element.name == 'ul':  # For lists
                    for li in element.find_all('li'):
                        list_item_text = li.get_text()
                        translated_list_item = translator.translate(list_item_text)

                        content_english += f"- {list_item_text}\n"
                        content_gujarati += f"- {translated_list_item}\n"

                elif element.name == 'ol':  # For ordered lists
                    for idx, li in enumerate(element.find_all('li'), 1):
                        list_item_text = li.get_text()
                        translated_list_item = translator.translate(list_item_text)

                        content_english += f"{idx}. {list_item_text}\n"
                        content_gujarati += f"{idx}. {translated_list_item}\n"

            # Write the section to PDF
            write_section_to_pdf(translated_title, title, content_gujarati, content_english)

# Iterate over unique URLs and scrape content
for url in unique_urls:
    scrape_and_generate_pdf(url)

# Finalize and save the PDF
pdf.save()
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
os.remove(pdf_file_name)
