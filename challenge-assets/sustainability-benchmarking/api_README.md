# ESG Survey Reporting API Documentation

This document provides detailed specifications for the ESG Survey Reporting API, adhering to the OpenAPI 3.0.0 specification. The API is designed to support operations related to Environmental, Social, and Governance (ESG) benchmarking, including document uploads, ESG indicator retrieval, service status checks, and PDF report generation for specified entities.

## Overview

- **OpenAPI Version**: 3.0.0
- **Title**: ESG Survey Reporting
- **Description**: A comprehensive API for uploading documents, generating reports, and retrieving ESG benchmarking data.
- **Version**: 1.0.0
- **Base URL**: `http://localhost:8080/api`

## API Endpoints

### Upload ESG Document

- **Endpoint**: `/esg/benchmark/upload/{entityName}`
- **Method**: POST
- **Description**: Upload an ESG document for a specific entity and retrieve related ESG benchmark documents.
- **Parameters**:
  - `entityName` (path): The name of the entity.
- **Request Body**:
  - `documentUpload`: Binary content of the document.
- **Responses**:
  - `200 OK`: Document uploaded successfully.

### Fetch Specific ESG Indicator

- **Endpoint**: `/esg/benchmark/upload/{entityName}/{esgType}/{esgIndicator}`
- **Method**: POST
- **Description**: Retrieve a specific ESG indicator for a given entity.
- **Parameters**:
  - `entityName`, `esgType`, `esgIndicator` (path): Identifiers for the entity and ESG indicators.
  - `question` (query, optional): Filter parameter.
- **Request Body**:
  - `documentUpload`: Binary content of the document.
- **Responses**:
  - `200 OK`: ESG indicator retrieved successfully.

### Service Keepalive

- **Endpoint**: `/esg/benchmark/keepalive`
- **Method**: GET
- **Description**: Check the operational status of the benchmarking service.
- **Responses**:
  - `200 OK`: Service is operational.

### Generate PDF Report

- **Endpoint**: `/esg/benchmark/pdf-report/{entityName}`
- **Method**: POST
- **Description**: Generate a PDF report for a specified entity.
- **Parameters**:
  - `entityName` (path): The name of the entity.
- **Request Body**:
  - `documentUpload`: Binary content of the document.
- **Responses**:
  - `200 OK`: PDF report generated successfully.

## Additional Endpoints

### Upload Document

- **Endpoint**: `/documents`
- **Method**: POST
- **Description**: Upload a document for ESG benchmarking.
- **Parameters**:
  - `document`: The document file to upload.
- **Responses**:
  - `200 OK`: Document uploaded successfully.
  - `400 Bad Request`: Invalid request format.

### Retrieve ESG Indicators

- **Endpoint**: `/indicators`
- **Method**: GET
- **Description**: Retrieve ESG indicators for a specified document.
- **Parameters**:
  - `documentId`: ID of the document.
- **Responses**:
  - `200 OK`: ESG indicators retrieved successfully.
  - `404 Not Found`: Document not found.

### Generate Report

- **Endpoint**: `/reports`
- **Method**: POST
- **Description**: Generate a report based on ESG indicators for a specified document.
- **Parameters**:
  - `documentId`: ID of the document.
- **Responses**:
  - `200 OK`: Report generated successfully.
  - `404 Not Found`: Document not found.

## Schemas

### MetaData

Defines the structure for metadata associated with ESG benchmarking, including questions, types, indicators, and citation details.

### Metrics

Outlines the metrics used to evaluate the benchmarking process, including time taken and model accuracy metrics like F1 score.

### ResponseInternalDetails

Describes the response format for document uploads, including entity name, benchmark details, and metrics.

### ResponseInternalDetailsScalar

Provides a detailed format for fetching specific ESG indicators, including questions, types, and detailed benchmarking results.

## Conclusion

This API serves as a vital tool for ESG benchmarking, facilitating document management, indicator retrieval, and report generation to support environmental, social, and governance initiatives.
