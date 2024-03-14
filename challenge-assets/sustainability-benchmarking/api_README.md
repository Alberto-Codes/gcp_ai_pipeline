# ESG Survey Reporting API Documentation

This document outlines the specifications of the ESG Survey Reporting API, structured according to the OpenAPI 3.0.0 standard. This API facilitates uploading documents for ESG benchmarking, fetching specific ESG indicators, checking service status, and generating PDF reports for given entities.

## Overview

- **OpenAPI Version**: 3.0.0
- **Title**: ESG Survey Reporting
- **Description**: API for uploading, generating reports for ESG Benchmarking
- **Version**: 1.0.0
- **Base URL**: `http://localhost:8080/api`

## Endpoints

### Upload ESG Document

- **Path**: `/esg/benchmark/upload/{entityName}`
- **Method**: POST
- **Summary**: Uploads an ESG document for a given entity and retrieves all ESG benchmark documents.
- **Parameters**:
  - `entityName` (path): The name of the entity for which the document is uploaded.
- **Request Body**:
  - `documentUpload`: The binary content of the document to upload.
- **Response**:
  - `200`: Document uploaded successfully, returning an array of ESG responses.

### Fetch Specific ESG Indicator

- **Path**: `/esg/benchmark/upload/{entityName}/{esgType}/{esgIndicator}`
- **Method**: POST
- **Summary**: Fetches a specific ESG indicator for a given entity.
- **Parameters**:
  - `entityName` (path): Name of the entity.
  - `esgType` (path): Type of the ESG.
  - `esgIndicator` (path): Specific ESG indicator to fetch.
  - `question` (query, optional): Number of items to skip before starting to collect the result set.
- **Request Body**:
  - `documentUpload`: The binary content of the document to upload.
- **Response**:
  - `200`: Successfully fetched the ESG indicator for the given entity.

### Service Keepalive

- **Path**: `/esg/benchmark/keepalive`
- **Method**: GET
- **Summary**: Checks the status of the benchmarking service.
- **Response**:
  - `200`: Service is up and running.

### Generate PDF Report

- **Path**: `/esg/benchmark/pdf-report/{entityName}`
- **Method**: POST
- **Summary**: Generates a PDF report for a given entity.
- **Parameters**:
  - `entityName` (path): Name of the entity for which to generate the report.
- **Request Body**:
  - `documentUpload`: The binary content of the document to upload.
- **Response**:
  - `200`: PDF report generated successfully.

## Components

### Schemas

#### MetaData

Defines the structure for metadata associated with an ESG benchmarking effort, including questions, ESG types (ESGScore, Environment, Social, Reporting), indicators, and details related to citations and pages.

#### Metrics

Details the metrics used to evaluate the benchmarking process, such as time taken, the model leveraged, and the F1 score.

#### ResponseInternalDetails

Outlines the response structure for an uploaded document, including the entity name, benchmark details (as an array of `MetaData`), and metrics.

#### ResponseInternalDetailsScalar

Similar to `ResponseInternalDetails`, but tailored for fetching specific ESG indicators, providing benchmark details in a scalar format.

## Conclusion

This API provides a comprehensive toolset for ESG benchmarking, including uploading documents, retrieving ESG indicators, and generating reports. It's designed to facilitate the integration of ESG benchmarking capabilities into broader systems or platforms.
