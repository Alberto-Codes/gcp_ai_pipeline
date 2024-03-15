import os
from typing import Optional

from google.api_core.client_options import ClientOptions
from google.cloud import documentai  # type: ignore

# TODO(developer): Uncomment these variables before running the sample.
project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
location = "us"  # Format is "us" or "eu"
processor_id = os.getenv(
    "DOCUMENT_AI_PROCESSOR_ID"
)  # Create processor before running sample
# file_path = "/path/to/local/pdf"
# mime_type = "application/pdf" # Refer to https://cloud.google.com/document-ai/docs/file-types for supported file types
# field_mask = "text,entities,pages.pageNumber"  # Optional. The fields to return in the Document object.
# processor_version_id = "YOUR_PROCESSOR_VERSION_ID" # Optional. Processor version to use
# gcs_output_uri = "YOUR_OUTPUT_URI" # Must end with a trailing slash `/`. Format: gs://bucket/directory/subdirectory/


from google.cloud import storage


def process_single_document(
    bucket_name: str,
    blob_name: str,
    mime_type: str = "application/pdf",
    field_mask: Optional[str] = None,
    processor_version_id: Optional[str] = None,
) -> None:
    # You must set the `api_endpoint` if you use a location other than "us".
    opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")

    client = documentai.DocumentProcessorServiceClient(client_options=opts)

    if processor_version_id:
        name = client.processor_version_path(
            project_id, location, processor_id, processor_version_id
        )
    else:
        name = client.processor_path(project_id, location, processor_id)

    # Create a storage client
    storage_client = storage.Client()

    # Get the bucket with the provided name
    bucket = storage_client.get_bucket(bucket_name)

    # Get the blob with the provided name
    blob = bucket.get_blob(blob_name)

    # Download the blob to a string, then convert it to bytes
    image_content = blob.download_as_text().encode()

    # Load binary data
    raw_document = documentai.RawDocument(content=image_content, mime_type=mime_type)

    process_options = documentai.ProcessOptions(
        individual_page_selector=documentai.ProcessOptions.IndividualPageSelector(
            pages=[1]
        )
    )

    request = documentai.ProcessRequest(
        name=name,
        raw_document=raw_document,
        field_mask=field_mask,
        process_options=process_options,
    )

    result = client.process_document(request=request)

    # For a full list of `Document` object attributes, reference this page:
    # https://cloud.google.com/document-ai/docs/reference/rest/v1/Document
    document = result.document

    # Read the text recognition output from the processor
    print("The document contains the following text:")
    print(document.text)
