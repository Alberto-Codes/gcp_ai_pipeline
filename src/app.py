import os
import time
import uuid

import requests
import streamlit as st
from google.cloud import documentai
from google.cloud import documentai_v1beta3 as documentai
from google.cloud import storage
from google.cloud.documentai_toolbox import gcs_utilities
from google.cloud.documentai_v1beta3.types import (
    BatchDocumentsInputConfig,
    BatchProcessRequest,
    Document,
    DocumentOutputConfig,
    GcsDocument,
    GcsDocuments,
    GcsPrefix,
    ProcessRequest,
    document,
    document_processor_service,
)
from PyPDF2 import PdfReader, PdfWriter
from document_processing.document_ai_service import batch_process_documents
from document_processing.process_single_document import process_single_document
import time 


# Now you can use batch_process_documents(...) in your app.py code


os.environ["LOCATION"] = "us"


# def process_pdf_with_document_ai(
#     processor_id, gcs_input_uri, gcs_output_uri, gcs_output_uri_prefix
# ):
#     # Set up the Document AI client
#     client = documentai.DocumentProcessorServiceClient()

#     # Create batches of documents for processing
#     gcs_bucket_name = gcs_input_uri.split("/")[2]  # Extract bucket name from gcs_input_uri
#     gcs_prefix = gcs_input_uri.split("/", 3)[-1]  # Extract prefix from gcs_input_uri

#     # Construct the request
#     request = documentai.BatchProcessRequest(
#         name=f"projects/{os.getenv('GOOGLE_CLOUD_PROJECT')}/locations/{os.getenv('LOCATION')}/processors/{processor_id}",
#         input_documents=documentai.BatchDocumentsInputConfig(
#             gcs_documents=documentai.GcsDocuments(
#                 documents=[documentai.GcsDocument(gcs_uri=gcs_input_uri, mime_type="application/pdf")]
#             )
#         ),
#         document_output_config=documentai.DocumentOutputConfig(
#             gcs_output_config=documentai.DocumentOutputConfig.GcsOutputConfig(
#                 gcs_uri=f"{gcs_output_uri}/{gcs_output_uri_prefix}/"
#             )
#         ),
#     )

#     # Send the request to the Document AI processor
#     operation = client.batch_process_documents(request)
#     operation.result(timeout=600)  # Wait for the operation to complete


def get_storage_client():
    return storage.Client(project=os.getenv("GOOGLE_CLOUD_PROJECT"))


def get_bucket(bucket_name):
    storage_client = get_storage_client()
    return storage_client.get_bucket(bucket_name)


def download_blob(blob, temp_file):
    blob.download_to_filename(temp_file)


def split_pdf(temp_file, pages_per_split=15):
    with open(temp_file, "rb") as fileobj:
        reader = PdfReader(fileobj)
        num_pages = len(reader.pages)

        for i in range(0, num_pages, pages_per_split):
            writer = PdfWriter()
            for j in range(i, min(i + pages_per_split, num_pages)):
                writer.add_page(reader.pages[j])

            with open(f"/tmp/temp_{i}.pdf", "wb") as output_pdf:
                writer.write(output_pdf)

            yield f"/tmp/temp_{i}.pdf"


def upload_blob(bucket, blob_name, content, content_type="application/pdf"):
    new_blob = bucket.blob(blob_name)
    new_blob.upload_from_string(content, content_type=content_type)


def delete_blob(blob):
    blob.delete()


def split_and_move_pdfs(
    source_bucket_name,
    dest_bucket_name,
    source_dir,
    dest_dir,
    # processor_id,
    json_bucket_name,
):
    source_bucket = get_bucket(source_bucket_name)
    dest_bucket = get_bucket(dest_bucket_name)
    json_bucket = get_bucket(json_bucket_name)

    blobs = source_bucket.list_blobs(prefix=source_dir)

    for blob in blobs:
        download_blob(blob, "/tmp/temp.pdf")
        blob_name, _ = os.path.splitext(blob.name)

        for i, temp_file in enumerate(split_pdf("/tmp/temp.pdf")):
            # split_blob_name = f"{blob.name}_{i}.pdf"
            split_blob_name = f"{blob_name}_{i}.pdf"
            upload_blob(dest_bucket, split_blob_name, temp_file)
            # time.sleep(5)
            # process_single_document(
            #     bucket_name=dest_bucket,
            #     blob_name=split_blob_name,
            #     # mime_type="application/pdf",

            # )


            gcs_input_uri = f"gs://{dest_bucket_name}/{split_blob_name}"
            gcs_output_uri = f"gs://{json_bucket}"
            gcs_output_uri_prefix = f"{dest_dir}{blob.name}_{i}_json"


        delete_blob(blob)


def search_pdfs(company_name, api_key, search_engine_id):
    search_url = "https://www.googleapis.com/customsearch/v1"
    query = f"{company_name} ESG OR environmental social governance filetype:pdf"
    params = {"key": api_key, "cx": search_engine_id, "q": query, "num": 3}
    response = requests.get(search_url, params=params)
    response.raise_for_status()
    search_results = response.json()
    pdf_urls = [
        item["link"]
        for item in search_results.get("items", [])
        if item.get("link").endswith(".pdf")
    ]
    return pdf_urls


def download_pdf(pdf_url, headers, retries=3, timeout=10):
    for attempt in range(retries):
        try:
            response = requests.get(pdf_url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.content
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.HTTPError,
            requests.exceptions.ReadTimeout,
        ) as e:
            st.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(2**attempt)
            else:
                st.error(f"Failed to download {pdf_url} after {retries} attempts.")
                return None


def handle_input(company_name, pdf_urls, user_id):
    st.write(f"Company Name: {company_name}")
    bucket_name = os.getenv("PDF_BUCKET_NAME")
    bucket = get_bucket(bucket_name)

    directory_name = f"{company_name}_{user_id}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }

    for pdf_url in pdf_urls:
        pdf_content = download_pdf(pdf_url, headers)
        if pdf_content is None:
            st.error(f"Failed to download {pdf_url}")
            continue

        file_name = pdf_url.split("/")[-1]
        blob_name = directory_name + file_name
        upload_blob(
            bucket, blob_name, pdf_content
        )  # Pass pdf_content instead of temp_file
        st.write(f"Uploaded {file_name} to {directory_name}")


def main():
    if "user_id" not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())

    api_key = os.getenv("API_KEY")
    search_engine_id = os.getenv("SEARCH_ENGINE_ID")

    st.title("Company Name Input")
    company_name = st.text_input("Enter the company name")

    if st.button("Submit"):
        pdf_urls = search_pdfs(company_name, api_key, search_engine_id)
        handle_input(company_name, pdf_urls, st.session_state.user_id)
        split_and_move_pdfs(
            os.getenv("PDF_BUCKET_NAME"),
            os.getenv("SPLIT_PDF_BUCKET_NAME"),
            f"{company_name}_{st.session_state.user_id}/",
            f"{company_name}_{st.session_state.user_id}/",
            # os.getenv("PROCESSOR_ID"),
            os.getenv("JSON_BUCKET_NAME"),
        )
        processor_id = os.getenv("DOCUMENT_AI_PROCESSOR_ID")
        gcs_input_prefix = f"gs://{os.getenv("SPLIT_PDF_BUCKET_NAME")}/{company_name}_{st.session_state.user_id}/"
        gcs_output_uri=f"gs://{os.getenv("JSON_BUCKET_NAME")}/{company_name}_{st.session_state.user_id}/"
        project_id=os.getenv("GOOGLE_CLOUD_PROJECT"),
        # gcs_output_uri = os.getenv("GCS_OUTPUT_URI")
        # gcs_output_uri_prefix = "processed_documents"

        batch_process_documents(
            project_id=project_id,
            location="us",
            processor_id=processor_id,
            gcs_output_uri=gcs_output_uri,
            gcs_input_prefix = gcs_input_prefix,
            input_mime_type="application/pdf"
        )



if __name__ == "__main__":
    main()
