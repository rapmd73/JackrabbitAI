import sys
from bs4 import BeautifulSoup

# Read raw HTML from standard input
html_input = sys.stdin.read()

# Parse the HTML
soup = BeautifulSoup(html_input, 'html.parser')

# Extract and print only the text content
print(soup.get_text())

