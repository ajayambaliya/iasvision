import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
import os
from deep_translator import GoogleTranslator

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

# Create an instance of the GoogleTranslator to translate to Gujarati
translator = GoogleTranslator(source='auto', target='gu')

# Function to scrape content from the provided URL and translate to Gujarati
def scrap_and_translate_content(url):
    print(f"Scraping: {url}")
    page_response = requests.get(url)
    page_soup = BeautifulSoup(page_response.content, 'html.parser')

    # Find the specific content area div
    content_area = page_soup.find('div', class_="flex flex-col w-full mt-6 lg:mt-0")
    gujarati_content = []

    if content_area:
        # Extract the title from the <h1> tag
        title = content_area.find('h1').get_text()
        translated_title = translator.translate(title)  # Translate the title to Gujarati
        gujarati_content.append(("title", translated_title))

        # Find article content under the <div id="article-content">
        article_content = content_area.find('div', id='article-content')

        if article_content:
            # Loop through each child element in the article content
            for element in article_content.find_all(recursive=False):
                if element.name == 'p':  # For paragraphs
                    paragraph_text = element.get_text()
                    translated_paragraph = translator.translate(paragraph_text)  # Translate paragraph
                    gujarati_content.append(("paragraph", translated_paragraph))

                elif element.name == 'h2':  # For sub-headings
                    sub_heading_text = element.get_text()
                    translated_sub_heading = translator.translate(sub_heading_text)  # Translate sub-heading
                    gujarati_content.append(("heading", translated_sub_heading))

                elif element.name == 'ul':  # For unordered lists
                    list_items = []
                    for li in element.find_all('li'):
                        list_item_text = li.get_text()
                        translated_list_item = translator.translate(list_item_text)  # Translate list item
                        list_items.append(translated_list_item)
                    gujarati_content.append(("ul", list_items))

                elif element.name == 'ol':  # For ordered lists
                    list_items = []
                    for li in element.find_all('li'):
                        list_item_text = li.get_text()
                        translated_list_item = translator.translate(list_item_text)  # Translate list item
                        list_items.append(translated_list_item)
                    gujarati_content.append(("ol", list_items))
    
    return gujarati_content

# Generate PDF using ReportLab
def generate_pdf(content_list, file_name):
    pdf = canvas.Canvas(file_name, pagesize=A4)
    pdf.setFont("Helvetica", 12)

    width, height = A4
    y_position = height - inch

    for content_type, content in content_list:
        if content_type == "title":
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawString(inch, y_position, content)
            y_position -= 0.5 * inch
        elif content_type == "heading":
            pdf.setFont("Helvetica-Bold", 14)
            pdf.drawString(inch, y_position, content)
            y_position -= 0.4 * inch
        elif content_type == "paragraph":
            pdf.setFont("Helvetica", 12)
            pdf.drawString(inch, y_position, content)
            y_position -= 0.3 * inch
        elif content_type == "ul":
            pdf.setFont("Helvetica", 12)
            for item in content:
                pdf.drawString(inch + 20, y_position, f"- {item}")
                y_position -= 0.3 * inch
        elif content_type == "ol":
            pdf.setFont("Helvetica", 12)
            for idx, item in enumerate(content, 1):
                pdf.drawString(inch + 20, y_position, f"{idx}. {item}")
                y_position -= 0.3 * inch

        if y_position < inch:
            pdf.showPage()
            y_position = height - inch

    pdf.save()

# Iterate over unique URLs and scrape content
all_gujarati_content = []
for url in unique_urls:
    all_gujarati_content.extend(scrap_and_translate_content(url))

# Save the generated PDF
pdf_file_name = f"visionias_current_affairs_{previous_date}.pdf"
generate_pdf(all_gujarati_content, pdf_file_name)
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
