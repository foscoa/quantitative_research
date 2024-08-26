'''
This script scrpaes the names on the website "https://www.cboe.com/us/futures/market_statistics/historical_data/"


'''

import requests
from bs4 import BeautifulSoup
import re
import os
import json

# URL of the website
url = "https://www.cboe.com/us/futures/market_statistics/historical_data/"

# Send a GET request to fetch the HTML content
response = requests.get(url)
response.raise_for_status()  # Check if the request was successful

# Parse the HTML content using BeautifulSoup
soup = BeautifulSoup(response.text, 'html.parser')

# Search for the script tag that contains the JS variable
script_tag = soup.find('script', string=re.compile("CTX.defaultProductList")).string.split(";")[1].split("=")[1]

# Convert the string to a dictionary
data = json.loads(script_tag)

# Extract all strings related to "green9"
green9_strings = []
for element in soup.find_all(string=re.compile("green9")):
    green9_strings.append(element)

# Output the results
print("CSV Links:")
for link in csv_links:
    print(link)

print("\nStrings containing 'green9':")
for string in green9_strings:
    print(string)

# Optionally, download the CSV files
for link in csv_links:
    csv_response = requests.get(link)
    file_name = link.split('/')[-1]
    with open(file_name, 'wb') as f:
        f.write(csv_response.content)
    print(f"Downloaded {file_name}")
