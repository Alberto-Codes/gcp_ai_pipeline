import os
import time
import uuid

import requests
import streamlit as st
from google.cloud import storage
from PyPDF2 import PdfReader, PdfWriter

from document_processing.datastore_refresh import import_documents_sample
from gcp_integration.search_convo import search_sample
from esg_score_fetch.sasb_fetch import fetch_sasb_pdf_links
import streamlit.components.v1 as components




def search_pdfs(company_name, api_key, search_engine_id):
    search_url = "https://www.googleapis.com/customsearch/v1"
    # Include 'ESG' and 'environmental social governance' in the query
    query = f"{company_name} ESG OR environmental OR social OR governance OR sustainability (MSCI OR Sustainalytics OR SBTi OR CDP OR GRI OR SASB OR TCFD) Assurance -filetype:pdf"
    params = {
        "key": api_key,
        "cx": search_engine_id,
        "q": query,
        "num": 10,  # Number of search results to return
    }
    response = requests.get(search_url, params=params, timeout=5)
    response.raise_for_status()
    search_results = response.json()
    pdf_urls = [
        item["link"]
        for item in search_results.get("items", [])
        if item.get("link").endswith(".pdf")
    ]
    return pdf_urls


def handle_input(company_name, pdf_urls):
    st.write(f"Company Name: {company_name}")
    storage_client = storage.Client(project=os.getenv("GOOGLE_CLOUD_PROJECT"))
    bucket_name = os.getenv("PDF_BUCKET_NAME")
    bucket = storage_client.get_bucket(bucket_name)

    # directory_name = f"{company_name}_{user_id}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }

    for pdf_url in pdf_urls:
        file_name = pdf_url.split("/")[-1]
        blob = bucket.blob(file_name)
        if not blob.exists():
            # If the file does not exist, download it
            success = False
            retries = 2  # Max retries
            for attempt in range(retries):
                try:
                    response = requests.get(
                        pdf_url, headers=headers, timeout=5
                    )  # Added timeout
                    response.raise_for_status()
                    # If request is successful, break out of the retry loop
                    success = True
                    break
                except (
                    requests.exceptions.ConnectionError,
                    requests.exceptions.HTTPError,
                    requests.exceptions.Timeout,
                ) as e:
                    st.error(f"Attempt {attempt + 1} failed: {e}")
                    time.sleep(1**attempt)  # Exponential backoff
            if not success:
                st.error(f"Failed to download {pdf_url} after {retries} attempts.")
                continue
            blob.upload_from_string(response.content, content_type="application/pdf")
            st.write(f"Uploaded {file_name} to {bucket_name}")
        else:
            st.write(f"{file_name} already exists in {bucket_name}")


def main():



    col1, col2 = st.columns(2)
    with col1:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        pdf_bucket = os.getenv("PDF_BUCKET_NAME")
        gcs_input_prefix = f"gs://{pdf_bucket}/"
        pdf_bucket_gcs_uri = f"{gcs_input_prefix}*"
        if "user_id" not in st.session_state:
            st.session_state.user_id = str(uuid.uuid4())

        api_key = os.getenv("API_KEY")
        search_engine_id = os.getenv("SEARCH_ENGINE_ID")

        st.title("Company Name Input")
        company_name = st.text_input("Enter the company name")



        if st.button("Submit"):
            pdf_urls = search_pdfs(company_name, api_key, search_engine_id)
            handle_input(company_name, pdf_urls)
            sasb_pdf_urls = fetch_sasb_pdf_links(company_name)
            if sasb_pdf_urls:
                st.write("Found SASB PDFs:")
                for url in sasb_pdf_urls:
                    st.write(url)
            handle_input(company_name, sasb_pdf_urls)
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
            location = "us"  # Values: "global"

            # Import the documents into the Datastore
            st.write("Importing documents into Datastore...")
            import_documents_sample(
                project_id=project_id,
                location=location,
                data_store_id=os.getenv("SEARCH_PDF_DATA_STORE_ID"),
                gcs_uri=pdf_bucket_gcs_uri,
            )
            import_documents_sample(
                project_id=project_id,
                location="global",
                data_store_id=os.getenv("CHAT_PDF_DATA_STORE_ID"),
                gcs_uri=pdf_bucket_gcs_uri,
            )
        # Get the search query from the user
        default_search_query = f"What do you know about {company_name} environment sustainability and governance?"
        search_query = st.text_input(
            "Please type your search query:", value=default_search_query
        )
        if st.button("Search"):
            search_response = search_sample(
                project_id=project_id,
                location="us",
                engine_id=os.getenv("SEARCH_AI_ENGINE_ID"),
                # search_query=f"Please explain ESG or environmental social governance efforts from this company named {company_name}.",
                search_query=search_query,
            )

            # Display the summary text
            summary_text = search_response.summary.summary_text
            st.markdown(f"**Summary:** {summary_text}")
            # Display the total size of the results
            st.markdown(f"**Total Results:** {search_response.total_size}")

            # Loop through each result
            for i, result in enumerate(search_response.results, start=1):
                # Display the result number
                st.markdown(f"**Result {i}**")

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

        
    with col2:
        
        st.title("Chat with the AI Agent")
        chat_agent_id = os.getenv('CHAT_AGENT_ID')
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        components.html(
                f"""
                <link rel="stylesheet" href="https://www.gstatic.com/dialogflow-console/fast/df-messenger/prod/v1/themes/df-messenger-default.css">
                <script src="https://www.gstatic.com/dialogflow-console/fast/df-messenger/prod/v1/df-messenger.js"></script>
                <df-messenger
                    project-id="{project_id}"
                    agent-id="{chat_agent_id}"
                    language-code="en"
                    max-query-length="-1">
                    <df-messenger-chat
                    chat-title="gcp ai pipeline chat">
                    </df-messenger-chat>
                </df-messenger>
                <style>
                    df-messenger {{
                        z-index: 999;
                        position: fixed;
                        bottom: 0;
                        right: 0;
                        top: 0;
                        width: 350px;
                    }}
                </style>
                """,
                height=600
        )

        # More of your Streamlit app code goes here

        # More of your Streamlit app code goes here



if __name__ == "__main__":
    main()
