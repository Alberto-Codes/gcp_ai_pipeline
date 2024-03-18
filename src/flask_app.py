import json
import os

import flask
import google.oauth2.credentials
import requests
from flask import Flask, jsonify, redirect, request, session, url_for
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from flask_talisman import Talisman

app = Flask(__name__)
Talisman(app)
app.config.update({"PREFERRED_URL_SCHEME": "https"})
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "DEFAULT_SECRET_KEY")



# add ping end point
@app.route("/ping")
def ping():
    return "pong"


@app.route("/import_documents", methods=["POST"])
def import_documents():
    if "credentials" not in session:
        return redirect(url_for("login"))

    credentials_dict = session["credentials"]
    credentials = Credentials.from_authorized_user_info(credentials_dict)

    if credentials.expired:
        credentials.refresh(Request())

    data = request.get_json()

    project_id = data.get("project_id")
    location = data.get("location")
    data_store_id = data.get("data_store_id")
    branch_id = 0
    gcs_uri = data.get("gcs_uri")

    headers = {
        "Authorization": f"Bearer {credentials.token}",
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
            "https://www.googleapis.com/auth/userinfo.profile"
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
            "https://www.googleapis.com/auth/userinfo.profile"
        ],
        state=state,
        redirect_uri=url_for("oauth2callback", _external=True, _scheme="https"),
    )

    authorization_response = request.url
    authorization_response = authorization_response.replace('http://', 'https://')
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
        + "</td></tr></table>"
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)
