from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
import pandas as pd
from fuzzywuzzy import fuzz, process
from sqlalchemy import create_engine
import logging

# Define functions

def ingest_csv():
    csv_path = 'dags/electricity-generation_emissions_sources_ownership.csv'
    df_csv = pd.read_csv(csv_path)
    df_csv['source'] = 'csv'
    df_csv.to_pickle('/tmp/df_csv.pkl')  # Save intermediate result
    logging.info("CSV Data Ingested")

def ingest_xlsx():
    xlsx_path = 'dags/Global-Nuclear-Power-Tracker-October-2023.csv'
    df_xlsx = pd.read_csv(xlsx_path)
    df_xlsx['source'] = 'Global Nuclear Data'
    df_xlsx.to_pickle('/tmp/df_xlsx.pkl')  # Save intermediate result
    logging.info("XLSX Data Ingested")

def clean_data():
    df_csv = pd.read_pickle('/tmp/df_csv.pkl')
    df_xlsx = pd.read_pickle('/tmp/df_xlsx.pkl')
    
    # Standardize and clean column names
    df_csv.columns = df_csv.columns.str.strip().str.lower().str.replace(' ', '_')
    df_xlsx.columns = df_xlsx.columns.str.strip().str.lower().str.replace(' ', '_')

    # Extract unique company names from both datasets
    company_names_csv = df_csv['company_name'].unique()
    company_names_xlsx = df_xlsx['owner'].unique()

    # Define a threshold for matching
    threshold = 80

    # Perform fuzzy matching to find the closest matches between company names
    matches = {
        name: match[0] if match[1] >= threshold else None
        for name in company_names_csv
        for match in [process.extractOne(name, company_names_xlsx, scorer=fuzz.token_set_ratio)]
    }

    df_csv['matched_company_name'] = df_csv['company_name'].map(matches)

    # Save cleaned data
    df_csv.to_pickle('/tmp/df_csv_clean.pkl')
    df_xlsx.to_pickle('/tmp/df_xlsx_clean.pkl')
    logging.info("Data Cleaned and Preprocessed")

def merge_data():
    df_csv = pd.read_pickle('/tmp/df_csv_clean.pkl')
    df_xlsx = pd.read_pickle('/tmp/df_xlsx_clean.pkl')
    
    df_merged = pd.merge(df_csv, df_xlsx, left_on='matched_company_name', right_on='owner', how='left')
    df_merged.to_pickle('/tmp/df_merged.pkl')
    logging.info("Data Merged")

def write_to_disk():
    df_merged = pd.read_pickle('/tmp/df_merged.pkl')
    df_merged.to_csv('/tmp/df_merged.csv', index=False)
    logging.info("Merged Data Written to Disk")

def load_to_postgresql():
    engine = create_engine('postgresql+psycopg2://username:password@localhost:5432/mydatabase')
    df_merged = pd.read_csv('dags/df_merged.csv')
    
    df_merged.to_sql('company_assets', engine, if_exists='replace', index=False)
    logging.info("Data Loaded to PostgreSQL")

# Define default args for the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 7, 14),
    'email': ['your_email@example.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Define the DAG
dag = DAG(
    'etl_pipeline',
    default_args=default_args,
    description='ETL pipeline to integrate company asset data',
    schedule_interval=timedelta(days=1),
)

# Define tasks
t1 = PythonOperator(
    task_id='ingest_csv',
    python_callable=ingest_csv,
    dag=dag,
)

t2 = PythonOperator(
    task_id='ingest_xlsx',
    python_callable=ingest_xlsx,
    dag=dag,
)

t3 = PythonOperator(
    task_id='clean_data',
    python_callable=clean_data,
    dag=dag,
)

t4 = PythonOperator(
    task_id='merge_data',
    python_callable=merge_data,
    dag=dag,
)

t5 = PythonOperator(
    task_id='write_to_disk',
    python_callable=write_to_disk,
    dag=dag,
)

# t6 = PythonOperator(
#     task_id='load_to_postgresql',
#     python_callable=load_to_postgresql,
#     dag=dag,
# )

# Set task dependencies
t1 >> t3
t2 >> t3
t3 >> t4
t4 >> t5
# t5 >> t6
