import json
import os

import flask
import google.oauth2.credentials
import requests
from flask import Flask, redirect, request, session, url_for
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "DEFAULT_SECRET_KEY")


@app.route("/login")
def login():
    credentials = json.loads(os.environ["OAUTH_CREDENTIALS"])

    flow = Flow.from_client_config(
        credentials,
        scopes=["https://www.googleapis.com/auth/cloud-platform", "profile", "email"],
        redirect_uri=url_for("oauth2callback", _external=True),
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

    credentials_json = json.loads(os.environ["OAUTH_CREDENTIALS"])
    credentials = credentials_json.get("web", {})

    flow = Flow.from_client_config(
        credentials,
        scopes=["https://www.googleapis.com/auth/cloud-platform", "profile", "email"],
        state=state,
        redirect_uri=url_for("oauth2callback", _external=True),
    )

    authorization_response = request.url
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
        + '<tr><td><a href="/test">Test an API request</a></td>'
        + "<td>Submit an API request and see a formatted JSON response. "
        + "    Go through the authorization flow if there are no stored "
        + "    credentials for the user.</td></tr>"
        + '<tr><td><a href="/authorize">Test the auth flow directly</a></td>'
        + "<td>Go directly to the authorization flow. If there are stored "
        + "    credentials, you still might not be prompted to reauthorize "
        + "    the application.</td></tr>"
        + '<tr><td><a href="/revoke">Revoke current credentials</a></td>'
        + "<td>Revoke the access token associated with the current user "
        + "    session. After revoking credentials, if you go to the test "
        + "    page, you should see an <code>invalid_grant</code> error."
        + "</td></tr>"
        + '<tr><td><a href="/clear">Clear Flask session credentials</a></td>'
        + "<td>Clear the access token currently stored in the user session. "
        + '    After clearing the token, if you <a href="/test">test the '
        + "    API request</a> again, you should go back to the auth flow."
        + "</td></tr></table>"
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)
