#!/bin/bash

# Ensure the Google Cloud SDK is initialized
gcloud init

# Create Cloud Storage Bucket
gsutil mb -l us-west4 gs://hackathon-pdf-bucket

# Set uniform bucket-level access
gsutil uniformbucketlevelaccess set on gs://hackathon-pdf-bucket

# Remove public access (if any)
gsutil iam ch -d allUsers:objectViewer gs://hackathon-pdf-bucket

# Additional setup commands here...

echo "Environment setup completed successfully."
