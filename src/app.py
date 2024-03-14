import os
import requests
import streamlit as st
from google.cloud import storage

def handle_input(company_name, pdf_url):
    # This function will handle the input, you can add your own logic here
    st.write(f'Company Name: {company_name}')

    # Create a storage client    
    storage_client = storage.Client(project=os.getenv("PROJECT_ID"))

    # The name for the new bucket
    bucket_name = os.getenv("BUCKET_NAME")  # Get the bucket name from an environment variable

    # Get the bucket
    bucket = storage_client.get_bucket(bucket_name)

    # Download the PDF file
    response = requests.get(pdf_url)
    response.raise_for_status()

    # Create a new blob and upload the file's content.
    blob = bucket.blob(f"{company_name}.pdf")
    blob.upload_from_string(response.content, content_type='application/pdf')

def main():
    st.title('Company Name Input')
    company_name = st.text_input('Enter the company name')
    pdf_url = st.text_input('Enter the PDF URL')
    if st.button('Submit'):
        handle_input(company_name, pdf_url)

if __name__ == "__main__":
    main()