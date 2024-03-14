import os
import streamlit as st
from google.cloud import storage

def handle_input(company_name):
    # This function will handle the input, you can add your own logic here
    st.write(f'Company Name: {company_name}')

    # Create a storage client    
    storage_client = storage.Client(project=os.getenv("PROJECT_ID"))

    # The name for the new bucket
    bucket_name = os.getenv("BUCKET_NAME")  # Get the bucket name from an environment variable

    # Get the bucket
    bucket = storage_client.get_bucket(bucket_name)

    # Create a new blob and upload the file's content.
    blob = bucket.blob("company_name.txt")
    blob.upload_from_string(company_name)

def main():
    st.title('Company Name Input')
    company_name = st.text_input('Enter the company name')
    if st.button('Submit'):
        handle_input(company_name)

if __name__ == "__main__":
    main()