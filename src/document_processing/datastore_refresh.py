from typing import Optional
from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine
import os

# Replace these variables with your actual values


def import_documents_sample(
    project_id: str,
    location: str,
    data_store_id: str,
    gcs_uri: Optional[str] = None,
) -> str:
    client_options = (
        ClientOptions(api_endpoint=f"{location}-discoveryengine.googleapis.com")
        if location != "global"
        else None
    )

    client = discoveryengine.DocumentServiceClient(client_options=client_options)

    parent = client.branch_path(
        project=project_id,
        location=location,
        data_store=data_store_id,
        branch="default_branch",
    )

    request = discoveryengine.ImportDocumentsRequest(
        parent=parent,
        gcs_source=discoveryengine.GcsSource(
            input_uris=[gcs_uri], data_schema="content"
        ),
        reconciliation_mode=discoveryengine.ImportDocumentsRequest.ReconciliationMode.FULL,
    )

    operation = client.import_documents(request=request)

    print(f"Waiting for operation to complete: {operation.operation.name}")
    response = operation.result()

    metadata = discoveryengine.ImportDocumentsMetadata(operation.metadata)

    print(response)
    print(metadata)

    return operation.operation.name


# Call the function with your parameters
# import_documents_sample(project_id, location, data_store_id, gcs_uri)
