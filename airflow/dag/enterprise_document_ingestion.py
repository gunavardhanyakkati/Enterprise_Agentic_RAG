from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.dags.enterprise_ingestion.scan import scan_sources
from airflow.dags.enterprise_ingestion.validate import validate_documents
from airflow.dags.enterprise_ingestion.parse import parse_documents
from airflow.dags.enterprise_ingestion.index import index_documents_hybrid
from airflow.dags.enterprise_ingestion.retention import apply_retention_policy

# Default DAG arguments
default_args = {
    "owner": "enterprise-kb",
    "depends_on_past": False,
    "start_date": datetime(2025, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=30),
}

# Create the DAG
dag = DAG(
    "enterprise_document_ingestion",
    default_args=default_args,
    description="Enterprise document pipeline: scan → validate → parse → index → retention",
    schedule="0 */4 * * *",  # Every 4 hours
    max_active_runs=1,
    catchup=False,
    tags=["enterprise", "documents", "ingestion", "hybrid-search"],
)

# Task definitions
scan_task = PythonOperator(
    task_id="scan_sources",
    python_callable=scan_sources,
    dag=dag,
)

validate_task = PythonOperator(
    task_id="validate_documents",
    python_callable=validate_documents,
    dag=dag,
)

parse_task = PythonOperator(
    task_id="parse_documents",
    python_callable=parse_documents,
    dag=dag,
)

index_task = PythonOperator(
    task_id="index_documents_hybrid",
    python_callable=index_documents_hybrid,
    dag=dag,
)

retention_task = PythonOperator(
    task_id="apply_retention_policy",
    python_callable=apply_retention_policy,
    dag=dag,
)

# Task dependencies: scan → validate → parse → index → retention
scan_task >> validate_task >> parse_task >> index_task >> retention_task

