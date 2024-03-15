import os
import time
import uuid  # Import UUID library

import requests
import streamlit as st
from google.cloud import storage
from PyPDF2 import PdfReader, PdfWriter

from document_processing.document_ai_service import batch_process_documents


def split_and_move_pdfs(source_bucket_name, dest_bucket_name, source_dir, dest_dir):
    storage_client = storage.Client(project=os.getenv("PROJECT_ID"))

    source_bucket = storage_client.get_bucket(source_bucket_name)
    dest_bucket = storage_client.get_bucket(dest_bucket_name)

    blobs = source_bucket.list_blobs(prefix=source_dir)

    for blob in blobs:
        # Download the blob to a temporary file
        blob.download_to_filename("/tmp/temp.pdf")

        # Split the PDF into smaller PDFs if necessary
        with open("/tmp/temp.pdf", "rb") as fileobj:
            reader = PdfReader(fileobj)
            num_pages = len(reader.pages)

            for i in range(0, num_pages, 15):
                writer = PdfWriter()
                for j in range(i, min(i + 15, num_pages)):
                    writer.add_page(reader.pages[j])

                # Save the smaller PDF to a temporary file
                with open(f"/tmp/temp_{i}.pdf", "wb") as output_pdf:
                    writer.write(output_pdf)

                # Upload the smaller PDF to the destination directory
                # new_blob = dest_bucket.blob(f'{dest_dir}{blob.name}_{i}.pdf')
                new_blob = dest_bucket.blob(f"{blob.name}_{i}.pdf")
                new_blob.upload_from_filename(
                    f"/tmp/temp_{i}.pdf", content_type="application/pdf"
                )

        # Delete the original blob
        # blob.delete()


def search_pdfs(company_name, api_key, search_engine_id):
    search_url = "https://www.googleapis.com/customsearch/v1"
    # Include 'ESG' and 'environmental social governance' in the query
    query = f"{company_name} ESG OR environmental social governance filetype:pdf"
    params = {
        "key": api_key,
        "cx": search_engine_id,
        "q": query,
        "num": 3,  # Number of search results to return
    }
    response = requests.get(search_url, params=params)
    response.raise_for_status()
    search_results = response.json()
    pdf_urls = [
        item["link"]
        for item in search_results.get("items", [])
        if item.get("link").endswith(".pdf")
    ]
    return pdf_urls


def handle_input(company_name, pdf_urls, user_id):
    st.write(f"Company Name: {company_name}")
    storage_client = storage.Client(project=os.getenv("PROJECT_ID"))
    bucket_name = os.getenv("PDF_BUCKET_NAME")
    bucket = storage_client.get_bucket(bucket_name)

    directory_name = f"{company_name}_{user_id}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }

    for pdf_url in pdf_urls:
        success = False
        retries = 3  # Max retries
        for attempt in range(retries):
            try:
                response = requests.get(
                    pdf_url, headers=headers, timeout=10
                )  # Added timeout
                response.raise_for_status()
                # If request is successful, break out of the retry loop
                success = True
                break
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.HTTPError,
            ) as e:
                st.error(f"Attempt {attempt + 1} failed: {e}")
                time.sleep(2**attempt)  # Exponential backoff
        if not success:
            st.error(f"Failed to download {pdf_url} after {retries} attempts.")
            continue

        file_name = pdf_url.split("/")[-1]
        blob = bucket.blob(directory_name + file_name)
        blob.upload_from_string(response.content, content_type="application/pdf")
        st.write(f"Uploaded {file_name} to {directory_name}")


def main():
    if "user_id" not in st.session_state:
        st.session_state.user_id = str(
            uuid.uuid4()
        )  # Set a unique user_id if not already set

    api_key = os.getenv("API_KEY")  # Your API key for the Custom Search JSON API
    search_engine_id = os.getenv("SEARCH_ENGINE_ID")  # Your Search Engine ID

    st.title("Company Name Input")
    company_name = st.text_input("Enter the company name")

    if st.button("Submit"):
        pdf_urls = search_pdfs(company_name, api_key, search_engine_id)
        handle_input(company_name, pdf_urls, st.session_state.user_id)
        # Call the split_and_move_pdfs function
        split_and_move_pdfs(
            os.getenv("PDF_BUCKET_NAME"),
            os.getenv("SPLIT_PDF_BUCKET_NAME"),
            f"{company_name}_{st.session_state.user_id}/",
            f"{company_name}_{st.session_state.user_id}/",
        )
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        processor_id = os.getenv("DOCUMENT_AI_PROCESSOR_ID")
        json_bucket = os.getenv("JSON_BUCKET_NAME")
        split_pdf_bucket = os.getenv("PDF_BUCKET_NAME")
        directory = f"{company_name}_{st.session_state.user_id}"
        gcs_output_uri = f"gs://{json_bucket}/{directory}/"
        gcs_input_prefix = f"gs://{split_pdf_bucket}/{directory}/"
        batch_process_documents(
            project_id=project_id,
            location="us",
            processor_id=processor_id,
            gcs_output_uri=gcs_output_uri,
            gcs_input_prefix=gcs_input_prefix,
        )


if __name__ == "__main__":
    main()
