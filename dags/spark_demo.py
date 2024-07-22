from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
from pyspark.sql import SparkSession
import fuzzymatcher
import logging

# Initialize Spark session
spark = SparkSession.builder \
    .appName("ETL Pipeline") \
    .getOrCreate()

# Define functions

def ingest_csv():
    csv_path = 'dags/electricity-generation_emissions_sources_ownership.csv'
    df_csv = spark.read.csv(csv_path, header=True, inferSchema=True)
    df_csv = df_csv.withColumn('source', 'csv')
    df_csv.write.parquet('/tmp/df_csv.parquet', mode='overwrite')
    logging.info("CSV Data Ingested")

def ingest_xlsx():
    xlsx_path = 'dags/Global-Nuclear-Power-Tracker-October-2023.csv'
    df_xlsx = spark.read.csv(xlsx_path, header=True, inferSchema=True)
    df_xlsx = df_xlsx.withColumn('source', 'Global Nuclear Data')
    df_xlsx.write.parquet('/tmp/df_xlsx.parquet', mode='overwrite')
    logging.info("XLSX Data Ingested")

def clean_data():
    df_csv = spark.read.parquet('/tmp/df_csv.parquet')
    df_xlsx = spark.read.parquet('/tmp/df_xlsx.parquet')
    
    # Standardize and clean column names
    df_csv = df_csv.toDF(*[c.strip().lower().replace(' ', '_') for c in df_csv.columns])
    df_xlsx = df_xlsx.toDF(*[c.strip().lower().replace(' ', '_') for c in df_xlsx.columns])

    # Extract unique company names from both datasets
    company_names_csv = [row['company_name'] for row in df_csv.select('company_name').distinct().collect()]
    company_names_xlsx = [row['owner'] for row in df_xlsx.select('owner').distinct().collect()]

    # Perform fuzzy matching
    matches = fuzzymatcher.fuzzy_left_join(df_csv.toPandas(), df_xlsx.toPandas(), 'company_name', 'owner')
    
    # Convert to Spark DataFrame and save
    df_cleaned = spark.createDataFrame(matches)
    df_cleaned.write.parquet('/tmp/df_cleaned.parquet', mode='overwrite')
    logging.info("Data Cleaned and Preprocessed")

def merge_data():
    df_cleaned = spark.read.parquet('/tmp/df_cleaned.parquet')
    
    df_merged = df_cleaned.join(df_cleaned, df_cleaned['company_name'] == df_cleaned['owner'], 'left')
    df_merged.write.parquet('/tmp/df_merged.parquet', mode='overwrite')
    logging.info("Data Merged")

def write_to_disk():
    df_merged = spark.read.parquet('/tmp/df_merged.parquet')
    df_merged.write.csv('/tmp/df_merged.csv', mode='overwrite', header=True)
    logging.info("Merged Data Written to Disk")

def load_to_postgresql():
    df_merged = spark.read.csv('dags/df_merged.csv', header=True, inferSchema=True)
    
    df_merged.write \
        .format('jdbc') \
        .option('url', 'jdbc:postgresql://localhost:5432/mydatabase') \
        .option('dbtable', 'company_assets') \
        .option('user', 'username') \
        .option('password', 'password') \
        .save()
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
    'spark_etl_pipeline',
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

