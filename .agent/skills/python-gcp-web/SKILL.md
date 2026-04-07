Overview

This skill defines the architectural standards for Python-based web services, Google Cloud Platform (GCP) infrastructure automation, and frontend integration.

1. Python & Web Backend

Version: Always target Python 3.11.

Framework: Use Flask for all web services and website routing.

Server-Side Rendering: Use Jinja2 templates and external CSS stylesheets for HTML output formatting.

Frontend: When building interactive user interfaces, use the React framework.

2. Database & GCP Standards

Firestore Policy: Use the native Google Cloud Firestore client libraries/APIs. Do not use the Firebase-branded SDKs or products unless explicitly requested.

Infrastructure as Code (IaC):

Whenever a GCP resource is designed (e.g., Cloud Storage buckets, Firestore instances), generate the corresponding gcloud CLI commands.

Append these commands to a shell script named gcp-setup.sh.

Ensure the script includes project ID variables and error handling.

3. Data Migration (Firestore to BigQuery)

When tasked with migrating data from a Firestore collection to a BigQuery table:

Mechanism: Provide a gcloud or Python-based automation command.

Schema Discovery: The logic must programmatically inspect the Firestore collection to determine the data types and structure.

Execution: Generate a BigQuery table schema that maps directly to the discovered Firestore structure before initiating the load.
