import os
import requests
from bs4 import BeautifulSoup
from googlesearch import search

def download_esg_report(company_name):
    query = f"{company_name} ESG report filetype:pdf"

    # Get the URLs of the search results
    for url in search(query, num_results=10):
        # Send a GET request to the URL
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all the <a> tags with href attributes containing 'pdf'
        for link in soup.find_all('a', href=True):
            if '.pdf' in link['href']:
                # Get the URL of the PDF file
                pdf_url = link['href']

                # Send a GET request to the PDF URL
                pdf_response = requests.get(pdf_url)

                # Get the name of the PDF file
                pdf_name = os.path.split(pdf_url)[-1]

                # Write the content of the response to a file
                with open(pdf_name, 'wb') as f:
                    f.write(pdf_response.content)

                print(f"Downloaded {pdf_name} from {pdf_url}")
                return

    print(f"No PDF found for {company_name}")

# Example usage
download_esg_report("Microsoft")