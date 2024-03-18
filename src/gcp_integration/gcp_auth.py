import google
import google.auth.transport.requests
import google.oauth2.credentials
from google.auth import compute_engine


def idtoken_from_metadata_server(url: str):
    """
    Use the Google Cloud metadata server in the Cloud Run (or AppEngine or Kubernetes etc.,)
    environment to create an identity token and add it to the HTTP request as part of an
    Authorization header.

    Args:
        url: The url or target audience to obtain the ID token for.
            Examples: http://www.example.com
    """

    request = google.auth.transport.requests.Request()
    # Set the target audience.
    # Setting "use_metadata_identity_endpoint" to "True" will make the request use the default application
    # credentials. Optionally, you can also specify a specific service account to use by mentioning
    # the service_account_email.
    credentials = compute_engine.IDTokenCredentials(
        request=request, target_audience=url, use_metadata_identity_endpoint=True
    )

    # Get the ID token.
    # Once you've obtained the ID token, use it to make an authenticated call
    # to the target audience.
    credentials.refresh(request)
    # print(credentials.token)
    print("Generated ID token.")


idtoken_from_metadata_server("https://www.googleapis.com/auth/cloud-platform")
