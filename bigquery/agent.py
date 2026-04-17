import os
from google.cloud import bigquery
from google.adk.agents import Agent
from dotenv import load_dotenv
import datetime

load_dotenv()

# Initialize the BigQuery Client
# Ensure GOOGLE_APPLICATION_CREDENTIALS is set in your .env or environment
# Lazy Lazy initializaion of BigQuery Client to avoid startup failures on Cloud Run
_client = None
def get_bq_client():
    global _client
    if _client is None:
        _client = bigquery.Client()
    return _client

# --- Tool 1: Metadata Fetcher ---
def get_table_schema(dataset_id: str, table_id: str):
    """
    Retrieves the schema (column names and types) for a BigQuery table.
    Use this first to understand what data is available before writing a query.
    """
    try:
        client = get_bq_client()
        table_ref = client.dataset(dataset_id).table(table_id)
        table = client.get_table(table_ref)
        schema_info = [{"name": f.name, "type": f.field_type} for f in table.schema]
        return {"table": f"{dataset_id}.{table_id}", "schema": schema_info}
    except Exception as e:
        return {"error": f"Failed to fetch schema: {str(e)}"}

# --- Tool 2: Precise Query Executor ---
def run_bigquery_query(sql_query: str):
    """
    Executes a SQL query against BigQuery and returns the results.
    ALWAYS use specific column names in your SELECT statement. 
    Limit results to 100 rows unless requested otherwise.
    """
    try:
        client = get_bq_client()
        query_job = client.query(sql_query)
        results = query_job.result()
        
        # Convert rows to list of dicts for the LLM
        rows = []
        for row in results:
            r_dict = dict(row)
            for k, v in r_dict.items():
                if isinstance(v, (datetime.datetime, datetime.date)):
                    r_dict[k] = v.isoformat()
            rows.append(r_dict)
            
        return {"row_count": len(rows), "data": rows}
    except Exception as e:
        return {"error": f"SQL Error: {str(e)}"}

# --- Tool 3: Fetch Report Pipelines ---
def fetch_report_pipelines(company_name: str, start_date: str = None, end_date: str = None, instructor: str = None, roi_rep: str = None):
    """
    Queries the report_pipelines view in BigQuery for a given company.
    Optionally filters by a date range, instructor name, or ROI rep name.
    
    Args:
        company_name: The name of the client/company (matches 'secondary_customer_from_pipeline').
        start_date: Optional start date in YYYY-MM-DD format.
        end_date: Optional end date in YYYY-MM-DD format.
        instructor: Optional instructor name to filter by.
        roi_rep: Optional ROI rep name to filter by.
    """
    try:
        # Building parameterized query safely
        query = "SELECT * FROM `roitraining-dashboard.airtable_sync.report_pipeline` WHERE REGEXP_REPLACE(LOWER(secondary_customer_from_pipeline), r'[^a-z0-9]', '') = REGEXP_REPLACE(LOWER(@company), r'[^a-z0-9]', '')"
        params = [bigquery.ScalarQueryParameter("company", "STRING", company_name)]
        
        # Handle date range filtering on pipeline event fields
        if start_date and end_date:
            query += """ AND (
                (start_date_from_pipeline_event >= @start_date AND start_date_from_pipeline_event <= @end_date) OR 
                (end_date_from_pipeline_event >= @start_date AND end_date_from_pipeline_event <= @end_date)
            )"""
            params.append(bigquery.ScalarQueryParameter("start_date", "STRING", start_date))
            params.append(bigquery.ScalarQueryParameter("end_date", "STRING", end_date))
        elif start_date:
            query += " AND (start_date_from_pipeline_event >= @start_date OR end_date_from_pipeline_event >= @start_date)"
            params.append(bigquery.ScalarQueryParameter("start_date", "STRING", start_date))
        elif end_date:
            query += " AND (start_date_from_pipeline_event <= @end_date OR end_date_from_pipeline_event <= @end_date)"
            params.append(bigquery.ScalarQueryParameter("end_date", "STRING", end_date))

        # Handle instructor and ROI rep filtering
        if instructor:
            query += " AND REGEXP_REPLACE(LOWER(instructor_first_last_name), r'[^a-z0-9]', '') LIKE CONCAT('%', REGEXP_REPLACE(LOWER(@instructor), r'[^a-z0-9]', ''), '%')"
            params.append(bigquery.ScalarQueryParameter("instructor", "STRING", instructor))
        if roi_rep:
            query += " AND REGEXP_REPLACE(LOWER(roi_rep_first_last_name), r'[^a-z0-9]', '') LIKE CONCAT('%', REGEXP_REPLACE(LOWER(@roi_rep), r'[^a-z0-9]', ''), '%')"
            params.append(bigquery.ScalarQueryParameter("roi_rep", "STRING", roi_rep))
            
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        client = get_bq_client()
        query_job = client.query(query, job_config=job_config)
        print("*" * 50)
        print(query )
        print("*" * 50)
        results = query_job.result()
        print(results)
        
        rows = []
        for row in results:
            r_dict = dict(row)
            for k, v in r_dict.items():
                if isinstance(v, (datetime.datetime, datetime.date)):
                    r_dict[k] = v.isoformat()
            rows.append(r_dict)
            
        return {"row_count": len(rows), "data": rows}
    except Exception as e:
        # Fallback to reports_pipeline if the table might be called reports_pipeline and not report_pipelines
        if "Not found: Table" in str(e) and "reports_pipeline" not in str(e):
             query = query.replace("report_pipelines", "reports_pipeline")
             try:
                 client = get_bq_client()
                 query_job = client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=params))
                 results = query_job.result()
                 rows = []
                 for row in results:
                     r_dict = dict(row)
                     for k, v in r_dict.items():
                         if isinstance(v, (datetime.datetime, datetime.date)):
                             r_dict[k] = v.isoformat()
                     rows.append(r_dict)
                 
                 return {"row_count": len(rows), "data": rows}
             except Exception as inner_e:
                 return {"error": f"Failed to fetch reports_pipeline: {str(inner_e)}"}
        return {"error": f"Failed to fetch report pipelines: {str(e)}"}

# --- The ADK Agent ---
bq_analyst = Agent(
    name="bq_analyst",
    model=os.getenv("MODEL", "gemini-2.5-flash"),
    instruction=(
        "You are a BigQuery Data Expert. Your goal is to answer user questions by querying data efficiently.\n\n"
        "STRATEGY:\n"
        "1. If the user asks about a table, first call 'get_table_schema' to see the available fields.\n"
        "2. Based on the schema, construct a standard SQL query that selects ONLY the necessary columns.\n"
        "3. Use 'run_bigquery_query' to fetch the data.\n"
        "4. Summarize the findings for the user.\n\n"
        "IMPORTANT: Never use 'SELECT *'. Always be specific to save costs and context window space."
    ),
    tools=[get_table_schema, run_bigquery_query]
)

root_agent = bq_analyst