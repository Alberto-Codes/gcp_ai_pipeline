import os
import time
import uuid  # Import UUID library

import requests
import streamlit as st
from google.cloud import storage
from PyPDF2 import PdfReader, PdfWriter

from document_processing.datastore_refresh import import_documents_sample
from document_processing.document_ai_service import batch_process_documents
from gcp_integration.search_convo import search_sample


def search_pdfs(company_name, api_key, search_engine_id):
    search_url = "https://www.googleapis.com/customsearch/v1"
    # Include 'ESG' and 'environmental social governance' in the query
    query = f"{company_name} ESG OR environmental social governance filetype:pdf"
    params = {
        "key": api_key,
        "cx": search_engine_id,
        "q": query,
        "num": 5,  # Number of search results to return
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
    storage_client = storage.Client(project=os.getenv("GOOGLE_CLOUD_PROJECT"))
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

    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    processor_id = os.getenv("DOCUMENT_AI_PROCESSOR_ID")
    json_bucket = os.getenv("JSON_BUCKET_NAME")
    pdf_bucket = os.getenv("PDF_BUCKET_NAME")
    directory = f"{company_name}_{st.session_state.user_id}"
    gcs_output_uri = f"gs://{json_bucket}/{directory}/"
    gcs_input_prefix = f"gs://{pdf_bucket}/{directory}/"
    data_store_id = os.getenv("DATA_STORE_ID")
    pdf_bucket_gcs_uri = f"{gcs_input_prefix}*"

    if st.button("Submit"):
        pdf_urls = search_pdfs(company_name, api_key, search_engine_id)
        handle_input(company_name, pdf_urls, st.session_state.user_id)

        # batch_process_documents(
        #     project_id=project_id,
        #     location="us",
        #     processor_id=processor_id,
        #     gcs_output_uri=gcs_output_uri,
        #     gcs_input_prefix=gcs_input_prefix,
        #     field_mask="text",
        # )
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = "us"  # Values: "global"
        data_store_id = os.getenv("DATASTORE_ID")
        # gcs_uri = f"gs://pdf-bucket-85204/lego_a68b4541-d83b-41fb-a871-a038e4e7050f/*" # Adjusted to include wildcard
        import_documents_sample(
            project_id=project_id,
            location=location,
            data_store_id=os.getenv("DATA_STORE_ID"),
            gcs_uri=pdf_bucket_gcs_uri,
        )
    # Get the search query from the user
    search_query = st.text_input("Please type your search query:")
    if st.button("Search"):
        search_response = search_sample(
            project_id=project_id,
            location="us",
            engine_id=os.getenv("AI_ENGINE_ID"),
            # search_query=f"Please explain ESG or environmental social governance efforts from this company named {company_name}.",
            search_query=search_query,
        )
        # Display the total size of the results
        st.markdown(f"**Total Results:** {search_response.total_size}")

        # Loop through each result
        for result in search_response.results:
            # Display the document ID
            st.markdown(f"**Document ID:** {result.id}")

            # Display the document title
            title = result.document.derived_struct_data.get("title")
            st.markdown(f"**Title:** {title}")

            # Display the document link
            link = result.document.derived_struct_data.get("link")
            st.markdown(f"**Link:** {link}")

            # Display the snippets
            snippets = result.document.derived_struct_data.get("snippets")
            for snippet in snippets:
                snippet_text = snippet.get("snippet")
                st.markdown(f"**Snippet:** {snippet_text}", unsafe_allow_html=True)

        # Display the summary text
        summary_text = search_response.summary.summary_text
        st.markdown(f"**Summary:** {summary_text}")


if __name__ == "__main__":
    main()
