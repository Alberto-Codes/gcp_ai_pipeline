import json
import os

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

    authorization_url, state = flow.authorization_url(
        "https://accounts.google.com/o/oauth2/auth",
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
    session["credentials"] = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }

    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)
