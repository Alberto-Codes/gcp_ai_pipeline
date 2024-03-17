import json
import os
import uuid

import requests
import streamlit as st
import streamlit.components.v1 as components

from document_processing.datastore_refresh import import_documents_sample

FLASK_BACKEND_SEARCH_URL = "http://localhost:5000/search_pdfs"
FLASK_BACKEND_HANDLE_URL = "http://localhost:5000/handle_input"
FLASK_BACKEND_URL = "http://localhost:5000"


def fetch_pdf_urls(company_name, api_key, search_engine_id):
    params = {
        "company_name": company_name,
        "api_key": api_key,
        "search_engine_id": search_engine_id,
    }
    response = requests.get(FLASK_BACKEND_SEARCH_URL, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to fetch PDF URLs: {response.text}")
        return []


def fetch_sasb_pdf_links(company_name):
    FLASK_BACKEND_URL = os.getenv("FLASK_BACKEND_URL")
    if not FLASK_BACKEND_URL:
        raise ValueError("Missing FLASK_BACKEND_URL environment variable")

    response = requests.get(
        f"{FLASK_BACKEND_URL}/fetch_sasb_pdf_links",
        params={"company_name": company_name},
    )

    pdf_links = []
    if response.status_code == 200:
        pdf_links = response.json().get("pdf_links", [])
        if pdf_links:
            st.write("Found SASB PDFs:")
            for url in pdf_links:
                st.write(url)
        else:
            st.write("No SASB PDFs found for this company.")
    else:
        st.error("Failed to fetch SASB PDF URLs.")

    return pdf_links


def upload_pdf_urls(pdf_urls):
    data = {"pdf_urls": pdf_urls}
    response = requests.post(FLASK_BACKEND_HANDLE_URL, json=data)
    if response.status_code == 200:
        result = response.json()
        if result["uploaded"]:
            uploaded_files = "<br>".join(result["uploaded"])
            st.markdown(f"Uploaded files:<br>{uploaded_files}", unsafe_allow_html=True)
        if result["already_exists"]:
            existing_files = "<br>".join(result["already_exists"])
            st.markdown(
                f"Files already exist:<br>{existing_files}", unsafe_allow_html=True
            )
        if result["failed"]:
            failed_files = "<br>".join(
                [f"{file_name}: {error}" for file_name, error in result["failed"]]
            )
            st.markdown(f"Failed files:<br>{failed_files}", unsafe_allow_html=True)
    else:
        st.error("Failed to process PDF URLs.")


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

        if st.button("Fetch PDFs"):
            pdf_urls = fetch_pdf_urls(company_name, api_key, search_engine_id)
            if pdf_urls:
                st.success("Found PDF URLs")
                for url in pdf_urls:
                    st.write(url)
                upload_pdf_urls(pdf_urls)
            sasb_pdf_urls = fetch_sasb_pdf_links(company_name)
            if sasb_pdf_urls:
                st.write("Found SASB PDFs:")
                for url in sasb_pdf_urls:
                    st.write(url)
                upload_pdf_urls(sasb_pdf_urls)
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
            location = "us"

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

        default_search_query = f"What is the net zero target for {company_name}?"
        search_query = st.text_input(
            "Please type your search query:", value=default_search_query
        )

        if st.button("Search AI"):
            payload = {
                "project": project_id,
                "location": "us",
                "data_store": os.getenv("SEARCH_PDF_DATA_STORE_ID"),
                "query": search_query,
                "preamble": "You are a robot that always responds with a year",
            }
            headers = {"Content-Type": "application/json"}

            response = requests.post(
                FLASK_BACKEND_URL + "/search_ai",
                data=json.dumps(payload),
                headers=headers,
            )

            if response.status_code == 200:
                search_response = response.json()

                corrected_query = search_response.get("correctedQuery", "")
                st.markdown(f"**Corrected Query:** {corrected_query}")

                summary_text = search_response.get("summary", {}).get("summaryText", "")
                st.markdown(f"**Answer to Query:** {summary_text}")

                results = search_response.get("results", [])

                for i, result in enumerate(results, start=1):

                    document_data = result.get("document", {}).get(
                        "derivedStructData", {}
                    )

                    title = document_data.get("title", "")
                    link = document_data.get("link", "").replace(
                        "gs://", "https://storage.cloud.google.com/"
                    )
                    snippet = document_data.get("snippets", [{}])[0].get("snippet", "")

                    st.markdown(
                        f"**[{i}]({link})**\n{title}\n{snippet}\n",
                        unsafe_allow_html=True,
                    )
            else:
                st.error(
                    f"Search failed with status code {response.status_code}: {response.text}"
                )

    with col2:

        st.title("Chat with the AI Agent")
        chat_agent_id = os.getenv("CHAT_AGENT_ID")
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
            height=600,
        )


if __name__ == "__main__":
    main()
