import os
import requests
import streamlit as st
from google.cloud import storage
import uuid  # Import UUID library
import time
import requests

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


def handle_input(company_name, pdf_urls, user_id):
    st.write(f'Company Name: {company_name}')
    storage_client = storage.Client(project=os.getenv("PROJECT_ID"))
    bucket_name = os.getenv("BUCKET_NAME")
    bucket = storage_client.get_bucket(bucket_name)

    directory_name = f"{company_name}_{user_id}/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }

    for pdf_url in pdf_urls:
        success = False
        retries = 3  # Max retries
        for attempt in range(retries):
            try:
                response = requests.get(pdf_url, headers=headers, timeout=10)  # Added timeout
                response.raise_for_status()
                # If request is successful, break out of the retry loop
                success = True
                break
            except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as e:
                st.error(f'Attempt {attempt + 1} failed: {e}')
                time.sleep(2 ** attempt)  # Exponential backoff
        if not success:
            st.error(f'Failed to download {pdf_url} after {retries} attempts.')
            continue

        file_name = pdf_url.split('/')[-1]
        blob = bucket.blob(directory_name + file_name)
        blob.upload_from_string(response.content, content_type='application/pdf')
        st.write(f'Uploaded {file_name} to {directory_name}')


def main():
    if 'user_id' not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())  # Set a unique user_id if not already set

    api_key = os.getenv("API_KEY")  # Your API key for the Custom Search JSON API
    search_engine_id = os.getenv("SEARCH_ENGINE_ID")  # Your Search Engine ID

    st.title('Company Name Input')
    company_name = st.text_input('Enter the company name')

    if st.button('Submit'):
        pdf_urls = search_pdfs(company_name, api_key, search_engine_id)
        handle_input(company_name, pdf_urls, st.session_state.user_id)

if __name__ == "__main__":
    main()
