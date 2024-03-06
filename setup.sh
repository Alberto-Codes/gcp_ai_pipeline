#!/bin/bash

# Set variables
BUCKET_NAME="hackathon-pdf-bucket"
ZIP_URL="https://archive.org/compress/NintendoPower1988-2004/formats=TEXT%20PDF&file=/NintendoPower1988-2004.zip"
ZIP_FILE="NintendoPower.zip"
REGION="us-west4"

# Check if gcloud is initialized, if not, initialize
if ! gcloud auth list | grep -q 'No credentialed accounts.'; then
  echo "GCloud SDK already initialized."
else
  echo "Initializing GCloud SDK..."
  gcloud init
fi

# Create Cloud Storage Bucket, if it does not exist
if ! gsutil ls gs://$BUCKET_NAME; then
  echo "Creating Cloud Storage Bucket: $BUCKET_NAME"
  gsutil mb -l $REGION gs://$BUCKET_NAME
else
  echo "Bucket $BUCKET_NAME already exists."
fi

# Set uniform bucket-level access
echo "Setting uniform bucket-level access for $BUCKET_NAME"
gsutil uniformbucketlevelaccess set on gs://$BUCKET_NAME

# Remove public access, if any
echo "Removing public access for $BUCKET_NAME"
gsutil iam ch -d allUsers:objectViewer gs://$BUCKET_NAME

# Download and extract PDFs, then upload to bucket
echo "Downloading ZIP file from Internet Archive..."
curl -L $ZIP_URL -o $ZIP_FILE

echo "Extracting ZIP file..."
unzip -o $ZIP_FILE -d NintendoPower

echo "Uploading extracted PDFs to Cloud Storage bucket: $BUCKET_NAME"
gsutil -m cp NintendoPower/*.pdf gs://$BUCKET_NAME/

echo "Environment setup and file upload completed successfully."
