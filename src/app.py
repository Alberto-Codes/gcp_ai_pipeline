import os
import requests
import streamlit as st
from google.cloud import storage

def search_pdfs(company_name, api_key, search_engine_id):
    search_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        'key': api_key,
        'cx': search_engine_id,
        'q': f"{company_name} filetype:pdf",
        'num': 10  # Number of search results to return
    }
    response = requests.get(search_url, params=params)
    response.raise_for_status()
    search_results = response.json()
    pdf_urls = [item['link'] for item in search_results.get('items', []) if item.get('link').endswith('.pdf')]
    return pdf_urls

def handle_input(company_name, pdf_urls):
    st.write(f'Company Name: {company_name}')

    storage_client = storage.Client(project=os.getenv("PROJECT_ID"))
    bucket_name = os.getenv("BUCKET_NAME")
    bucket = storage_client.get_bucket(bucket_name)

    for i, pdf_url in enumerate(pdf_urls, start=1):
        response = requests.get(pdf_url)
        response.raise_for_status()
        blob = bucket.blob(f"{company_name}_{i}.pdf")
        blob.upload_from_string(response.content, content_type='application/pdf')

def main():
    api_key = os.getenv("API_KEY")  # Your API key for the Custom Search JSON API
    search_engine_id = os.getenv("SEARCH_ENGINE_ID")  # Your Search Engine ID

    st.title('Company Name Input')
    company_name = st.text_input('Enter the company name')
    if st.button('Submit'):
        pdf_urls = search_pdfs(company_name, api_key, search_engine_id)
        handle_input(company_name, pdf_urls)

if __name__ == "__main__":
    main()
