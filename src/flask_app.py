import json
import os

import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request
from google.auth import default
from google.auth.transport.requests import Request
from google.cloud import storage

credentials, project = default()


if not credentials.valid:
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

access_token = credentials.token

app = Flask(__name__)

@app.route('/import_documents', methods=['POST'])
def import_documents():
    data = request.get_json()

    project_id = data.get('project_id')
    location = data.get('location')
    data_store_id = data.get('data_store_id')
    # branch_id = data.get('branch_id')
    branch_id = 0
    gcs_uri = data.get('gcs_uri')

    # credentials, project = default()

    # if not credentials.valid:
    #     if credentials.expired and credentials.refresh_token:
    #         credentials.refresh(Request())



    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    if location == "us":
        url = f"https://us-discoveryengine.googleapis.com/v1alpha/projects/{project_id}/locations/{location}/collections/default_collection/dataStores/{data_store_id}/branches/{branch_id}/documents:import"
    else:
        url = f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}/locations/{location}/collections/default_collection/dataStores/{data_store_id}/branches/{branch_id}/documents:import"
    body = {
        "gcsSource": {
            "input_uris": [gcs_uri],
            "data_schema": "content"
        },
        "reconciliationMode": "INCREMENTAL",
    }

    response = requests.post(url, headers=headers, json=body)

    if response.status_code == 200:
        return jsonify(response.json())
    else:
        return (
            jsonify(
                {
                    "error": "Request failed",
                    "status_code": response.status_code,
                    "message": response.text,
                }
            ),
            response.status_code,
        )

@app.route("/search_ai", methods=["POST"])
def search_with_discovery_engine():

    data = request.get_json()
    query = data.get("query", "")
    preamble = data.get("preamble", "")
    project_id = data.get("project_id")
    location = data.get("location", "")
    data_store_id = data.get("data_store_id", "")

    payload = {
        "query": query,
        "pageSize": 10,
        "queryExpansionSpec": {"condition": "AUTO"},
        "spellCorrectionSpec": {"mode": "AUTO"},
        "contentSearchSpec": {
            "summarySpec": {
                "summaryResultCount": 5,
                "modelPromptSpec": {"preamble": preamble},
                "modelSpec": {"version": "preview"},
                "ignoreAdversarialQuery": True,
                "includeCitations": True,
            },
            "snippetSpec": {"maxSnippetCount": 1, "returnSnippet": True},
        },
    }
    url = f"https://us-discoveryengine.googleapis.com/v1alpha/projects/{project_id}/locations/{location}/collections/default_collection/dataStores/{data_store_id}/servingConfigs/default_search:search"



    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        return jsonify(response.json())
    else:
        return (
            jsonify(
                {
                    "error": "Request failed",
                    "status_code": response.status_code,
                    "message": response.text,
                }
            ),
            response.status_code,
        )


def search_pdfs(company_name, api_key, search_engine_id):
    search_url = "https://www.googleapis.com/customsearch/v1"
    query = f"{company_name} ESG OR environmental social governance filetype:pdf"
    params = {
        "key": api_key,
        "cx": search_engine_id,
        "q": query,
        "num": 10,
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


@app.route("/search_pdfs", methods=["GET"])
def handle_search():
    company_name = request.args.get("company_name")
    api_key = request.args.get("api_key")
    search_engine_id = request.args.get("search_engine_id")
    if not (company_name and api_key and search_engine_id):
        return jsonify({"error": "Missing required parameters"}), 400
    try:
        pdf_urls = search_pdfs(company_name, api_key, search_engine_id)
        return jsonify(pdf_urls), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/fetch_sasb_pdf_links", methods=["GET"])
def fetch_sasb_pdf_links_endpoint():
    company_name = request.args.get("company_name")
    if not company_name:
        return jsonify({"error": "Company name is required"}), 400

    url = "https://sasb.ifrs.org/company-use/sasb-reporters/"
    response = requests.get(url)

    cookie = response.cookies.get_dict()

    cookie_str = "; ".join([f"{k}={v}" for k, v in cookie.items()])

    url = "https://sasb.ifrs.org/wp-json/sasb/v1/reportsSearch"
    params = {"search": company_name, "format": "html"}
    headers = {
        "authority": "sasb.ifrs.org",
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "cookie": cookie_str,
        "referer": "https://sasb.ifrs.org/company-use/sasb-reporters/",
        "sec-ch-ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    }

    response = requests.get(url, params=params, headers=headers)

    if response.status_code != 200:
        return []

    data = json.loads(response.text)

    soup = BeautifulSoup(data["html"], "html.parser")

    links = soup.find_all("a")

    base_url = "https://sasb.ifrs.org/company-use/sasb-reporters/"

    pdf_links = [
        (
            base_url + link.get("href")
            if not link.get("href").startswith("http")
            else link.get("href")
        )
        for link in links
    ]
    return jsonify({"pdf_links": pdf_links})


@app.route("/handle_input", methods=["POST"])
def handle_input():
    data = request.json
    pdf_urls = data["pdf_urls"]
    bucket_name = os.getenv("PDF_BUCKET_NAME")
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    uploaded_files = []
    failed_files = []
    already_exists_files = []

    for pdf_url in pdf_urls:
        file_name = pdf_url.split("/")[-1]
        blob = bucket.blob(file_name)
        if blob.exists():
            already_exists_files.append(file_name)
        else:
            try:
                response = requests.get(pdf_url, timeout=5)
                response.raise_for_status()
                blob.upload_from_string(
                    response.content, content_type="application/pdf"
                )
                uploaded_files.append(file_name)
            except Exception as e:
                failed_files.append((file_name, str(e)))

    return jsonify(
        {
            "uploaded": uploaded_files,
            "already_exists": already_exists_files,
            "failed": failed_files,
        }
    )


if __name__ == "__main__":
    app.run(debug=True)
