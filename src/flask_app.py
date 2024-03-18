import csv
import json
import os
import time
from functools import wraps

import flask
import google.oauth2.credentials
import requests
from flask import Flask, jsonify, redirect, request, session, url_for
from flask_talisman import Talisman
from google.auth.transport.requests import Request
from google.cloud import storage
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

app = Flask(__name__)
Talisman(app)
app.config.update({"PREFERRED_URL_SCHEME": "https"})
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "DEFAULT_SECRET_KEY")


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if "Authorization" in request.headers:
            token = request.headers["Authorization"]
            token = token.split(" ")[1] if token.startswith("Bearer ") else None

        if not token:
            return jsonify({"message": "Token is missing!"}), 401

        return f(*args, **kwargs)

    return decorated


@app.route("/esg/benchmark/upload/<entityName>", methods=["POST"])
@token_required
def upload_esg_document(entityName):
    if "documentUpload" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["documentUpload"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    # Validate file type here
    if not file.filename.endswith(".pdf"):
        return jsonify({"error": "File is not a PDF"}), 400

    bucket_name = os.getenv("PDF_BUCKET_NAME")
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    # Modify file_name to include entityName for organized storage
    file_name = f"{entityName}/{file.filename}"  # Dynamic path based on entityName
    blob = bucket.blob(file_name)

    response_data = {
        "entityName": entityName,
        "uploaded": [],
        "already_exists": [],
        "failed": [],
    }

    if blob.exists():
        response_data["already_exists"].append(file_name)
    else:
        try:
            blob.upload_from_file(file, content_type="application/pdf")
            response_data["uploaded"].append(file_name)
        except Exception as e:
            response_data["failed"].append((file_name, str(e)))

    return jsonify(response_data)


# Replace @token_required with your actual token verification decorator


@app.route(
    "/esg/benchmark/upload/<entityName>/<esgType>/<esgIndicator>", methods=["POST"]
)
@token_required
def upload_esg_benchmark(entityName, esgType, esgIndicator):
    start_time = time.time()
    # Assuming 'parameters.csv' is structured with 'entityName,esgType,esgIndicator,preamble,query' headers
    with open("parameters.csv", mode="r", encoding="utf-8") as csv_file:
        csv_reader = csv.DictReader(csv_file)
        for row in csv_reader:
            if row["esgType"] == esgType and row["esgIndicator"] == esgIndicator:
                preamble = row["preamble"]
                query = row["query"].format(entityName=entityName)
                break
        else:
            return (
                jsonify(
                    {
                        "error": "Parameters not found for given esgType, and esgIndicator"
                    }
                ),
                404,
            )

    auth_header = request.headers.get("Authorization")
    token = auth_header.split(" ")[1] if auth_header else ""

    data = request.get_json()
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
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    response = requests.post(url, headers=headers, json=payload)
    # Process the API response
    if response.status_code == 200:
        api_response = response.json()
        summaryText = api_response.get("summary", {}).get("summaryText", "")
        citationDetails = api_response["results"][0]["document"]["link"]
        

        # Extract and transform data from the response
        benchmark_details = {
            "question": query,
            "esgType": esgType,
            "esgIndicators": esgIndicator,
            "primaryDetails": summaryText,
            "secondaryDetails": [],
            "citationDetails": citationDetails,
            "pageNumber": 1,  # This is a placeholder
        }

        if api_response.get("results"):
            # If there are multiple documents, you might want to aggregate them differently
            # For simplicity, this example uses the first document
            first_result = api_response["results"][0]["document"]
            derived_struct_data = first_result["derivedStructData"]
            benchmark_details["secondaryDetails"] = [
                snippet["snippet"] for snippet in derived_struct_data["snippets"]
            ]
            # benchmark_details["citationDetails"] = derived_struct_data["link"]
            # pageNumber could be dynamically determined based on document content
             
            end_time = time.time()
            time_taken = end_time-start_time
        # Prepare the final JSON response
        response_payload = {
            "entityName": entityName,
            "benchmarkDetails": [
                benchmark_details
            ],  # Note: Adjusted to a list to match the expected array type
            "Metrics": {
                "timeTaken": time_taken,  # Placeholder, should be calculated based on your logic
                "dataStore": data_store_id,  # Example, adjust as needed
                "f1Score": "f1Score not available",  # Placeholder, should be calculated based on your logic
            },
        }

        return jsonify(response_payload), 200
    else:
        # Handle errors or unsuccessful responses
        return (
            jsonify(
                {"error": "Failed to fetch data", "status_code": response.status_code}
            ),
            response.status_code,
        )


# add ping end point
@app.route("/ping")
def ping():
    return "pong"


@app.route("/search_ai", methods=["POST"])
@token_required
def search_with_discovery_engine():
    auth_header = request.headers.get("Authorization")
    token = auth_header.split(" ")[1] if auth_header else ""

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
        "Authorization": f"Bearer {token}",
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


@app.route("/import_documents", methods=["POST"])
@token_required
def import_documents():
    auth_header = request.headers.get("Authorization")
    token = auth_header.split(" ")[1] if auth_header else ""

    data = request.get_json()

    project_id = data.get("project_id")
    location = data.get("location")
    data_store_id = data.get("data_store_id")
    branch_id = 0
    gcs_uri = data.get("gcs_uri")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # Rest of your code...

    if location == "us":
        url = f"https://us-discoveryengine.googleapis.com/v1alpha/projects/{project_id}/locations/{location}/collections/default_collection/dataStores/{data_store_id}/branches/{branch_id}/documents:import"
    else:
        url = f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}/locations/{location}/collections/default_collection/dataStores/{data_store_id}/branches/{branch_id}/documents:import"
    body = {
        "gcsSource": {"input_uris": [gcs_uri], "data_schema": "content"},
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


@app.route("/login")
def login():
    credentials = json.loads(os.environ["OAUTH_CREDENTIALS"])

    flow = Flow.from_client_config(
        credentials,
        scopes=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/cloud-platform",
            "https://www.googleapis.com/auth/userinfo.profile",
        ],
        redirect_uri=url_for("oauth2callback", _external=True, _scheme="https"),
    )

    # Corrected authorization_url call
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
    )

    # Store the state in the session so it can be used in the callback
    session["state"] = state

    return redirect(authorization_url)


@app.route("/oauth2callback")
def oauth2callback():
    state = session["state"]

    credentials = json.loads(os.environ["OAUTH_CREDENTIALS"])

    flow = Flow.from_client_config(
        credentials,
        scopes=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/cloud-platform",
            "https://www.googleapis.com/auth/userinfo.profile",
        ],
        state=state,
        redirect_uri=url_for("oauth2callback", _external=True, _scheme="https"),
    )

    authorization_response = request.url
    authorization_response = authorization_response.replace("http://", "https://")
    flow.fetch_token(authorization_response=authorization_response)

    credentials = flow.credentials
    session["credentials"] = credentials_to_dict(credentials)

    return redirect(url_for("index"))


@app.route("/")
def index():
    return print_index_table()


@app.route("/revoke")
def revoke():
    if "credentials" not in flask.session:
        return (
            'You need to <a href="/authorize">authorize</a> before '
            + "testing the code to revoke credentials."
        )

    credentials = google.oauth2.credentials.Credentials(**session["credentials"])

    revoke = requests.post(
        "https://oauth2.googleapis.com/revoke",
        params={"token": credentials.token},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )

    status_code = getattr(revoke, "status_code")
    if status_code == 200:
        return "Credentials successfully revoked." + print_index_table()
    else:
        return "An error occurred." + print_index_table()


@app.route("/clear")
def clear_credentials():
    if "credentials" in session:
        del session["credentials"]
    return "Credentials have been cleared.<br><br>" + print_index_table()


def credentials_to_dict(credentials):
    return {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }


def print_index_table():
    return (
        "<table>"
        + '<tr><td><a href="/import_documents">Import documents</a></td>'
        + "<td>Submit an API request to import documents. "
        + "    Go through the authorization flow if there are no stored "
        + "    credentials for the user.</td></tr>"
        + '<tr><td><a href="/login">Start the auth flow</a></td>'
        + "<td>Go directly to the authorization flow. If there are stored "
        + "    credentials, you still might not be prompted to reauthorize "
        + "    the application.</td></tr>"
        + '<tr><td><a href="/revoke">Revoke current credentials</a></td>'
        + "<td>Revoke the access token associated with the current user "
        + "    session. After revoking credentials, if you go to the import documents "
        + "    page, you should see an <code>invalid_grant</code> error."
        + "</td></tr>"
        + '<tr><td><a href="/clear">Clear Flask session credentials</a></td>'
        + "<td>Clear the access token currently stored in the user session. "
        + '    After clearing the token, if you <a href="/import_documents">import documents</a> '
        + "    again, you should go back to the auth flow."
        + "</td></tr>"
        + '<tr><td><a href="/ping">Ping the server</a></td>'
        + "<td>Check if the server is alive. If the server is running, "
        + "    you should get a 'Pong!' response."
        + "</td></tr>"
        + '<tr><td><a href="/search_ai">Search with AI</a></td>'
        + "<td>Submit a search query to the AI Discovery Engine. "
        + "    You need to be authorized and provide a JSON payload with the search parameters."
        + "</td></tr></table>"
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)
