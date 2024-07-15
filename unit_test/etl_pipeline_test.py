import unittest
import pandas as pd
from etl_pipeline import ingest_csv, ingest_xlsx, clean_data, merge_data, load_to_postgresql

class TestETLPipeline(unittest.TestCase):

    def setUp(self):
        # Set up any necessary resources or test data
        self.csv_path = '/workspaces/ETL-pipeline/dags/electricity-generation_emissions_sources_ownership.csv'
        self.xlsx_path = '/workspaces/ETL-pipeline/dags/Global-Nuclear-Power-Tracker-October-2023.csv'

    def tearDown(self):
        # Clean up after each test if necessary
        pass

    def test_ingest_csv(self):
        # Test CSV ingestion
        ingest_csv()
        df_csv = pd.read_pickle('/tmp/df_csv.pkl')
        self.assertTrue('source' in df_csv.columns)
        self.assertEqual(df_csv['source'].unique(), ['csv'])

    def test_ingest_xlsx(self):
        # Test XLSX ingestion
        ingest_xlsx()
        df_xlsx = pd.read_pickle('/tmp/df_xlsx.pkl')
        self.assertTrue('source' in df_xlsx.columns)
        self.assertEqual(df_xlsx['source'].unique(), ['Global Nuclear Data'])

    def test_clean_data(self):
        # Test data cleaning and preprocessing
        clean_data()
        df_csv = pd.read_pickle('/tmp/df_csv_clean.pkl')
        df_xlsx = pd.read_pickle('/tmp/df_xlsx_clean.pkl')
        # Example assertions for cleaned data
        self.assertEqual(df_csv.columns.str.lower().str.replace(' ', '_').tolist(), df_csv.columns.tolist())

    def test_merge_data(self):
        # Test data merging
        merge_data()
        df_merged = pd.read_pickle('/tmp/df_merged.pkl')
        # Example assertion for merged data
        self.assertTrue('matched_company_name' in df_merged.columns)

    # def test_load_to_postgresql(self):
    #     # Test data loading into PostgreSQL
    #     load_to_postgresql()
        # Example assertion for data in PostgreSQL (if possible)
        # Ensure to set up a test database or mock the PostgreSQL connection for testing
        # Check if data is correctly loaded

if __name__ == '__main__':
    unittest.main()
