import unittest
import os
import pandas as pd
import numpy as np
import tempfile

from unittest.mock import patch

from price_calculation import DataSourceType, DataHandler, PriceCalculator


# --- Tests for DataHandler ---
class TestDataHandler(unittest.TestCase):
    """
    Test suite for the DataHandler class.
    Covers file reading/writing, large file size validation, and
    error handling for unimplemented data source types.
    """
    def setUp(self):
        self.temp_dir_obj = tempfile.TemporaryDirectory()
        self.tmp_path = self.temp_dir_obj.name

    def tearDown(self):
        self.temp_dir_obj.cleanup()

    def test_data_handler_file_read_write(self):
        """Tests successful file reading and writing operations."""
        source_file = os.path.join(self.tmp_path, "source.csv")
        export_file = os.path.join(self.tmp_path, "result.csv")

        df_source = pd.DataFrame({
            'Name': ['ProductA', 'ProductB'],
            'Datetime': ['2023-01-01 10:00:00', '2023-01-01 10:00:00'],
            'Amount': [10, 5],
            'Price': [100, 20],
            'Purity': ['Pure', 'Impure']
        })
        df_source.to_csv(source_file, index=False)

        handler = DataHandler(DataSourceType.FILE, str(source_file), str(export_file))
        retrieved_df = handler.retrieve_df()

        pd.testing.assert_frame_equal(df_source, retrieved_df)

        handler.export_df(retrieved_df)
        exported_df = pd.read_csv(export_file)
        pd.testing.assert_frame_equal(df_source, exported_df)

    @patch('os.path.getsize')
    def test_data_handler_large_file_error(self, mock_getsize):
        """Tests that ValueError is raised for files exceeding the maximum allowed size."""
        source_file = os.path.join(self.tmp_path, "large_file.csv")
        export_file = os.path.join(self.tmp_path, "result.csv")

        with open(source_file, 'w') as f:
            f.write("header\n")
            f.write("a" * 100)

        handler = DataHandler(DataSourceType.FILE, str(source_file), str(export_file))

        mock_getsize.return_value = handler.MAX_FILE_SIZE_GB * (1024**3) + 1

        with self.assertRaisesRegex(ValueError, "File is too large"):
            handler.retrieve_df()

    def test_data_handler_not_implemented_errors(self):
        """Tests that NotImplementedError is raised for currently unsupported data sources (Database, API)."""
        handler_db = DataHandler(DataSourceType.DATABASE, "", "")
        handler_api = DataHandler(DataSourceType.API, "", "")

        dummy_df = pd.DataFrame()

        # Verify retrieve_df raises NotImplementedError for DB and API
        with self.assertRaisesRegex(NotImplementedError, "Database query is not implemented"):
            handler_db.retrieve_df()
        with self.assertRaisesRegex(NotImplementedError, "API fetch is not implemented"):
            handler_api.retrieve_df()

        # Verify export_df raises NotImplementedError for DB and API
        with self.assertRaisesRegex(NotImplementedError, "Database save is not implemented"):
            handler_db.export_df(dummy_df)
        with self.assertRaisesRegex(NotImplementedError, "API post is not implemented"):
            handler_api.export_df(dummy_df)


# --- Tests for PriceCalculator ---
class TestPriceCalculator(unittest.TestCase):
    """
    Test suite for the PriceCalculator class.
    Covers data serialization, various validation rules, timezone conversion,
    and the complex total price calculation logic.
    """
    def setUp(self):
        """Sets up common sample DataFrame data used across PriceCalculator tests."""
        self.sample_df_data = {
            'Name': ['ProductA', 'ProductA', 'ProductB', 'ProductB'],
            'Datetime': ['2023-01-01 10:00:00', '2023-01-01 11:00:00', '2023-01-01 10:00:00', '2023-01-01 11:00:00'],
            'Amount': [10, 5, 20, 15],
            'Price': [100, 200, 120, 210],
            'Purity': ['Pure', 'Impure', 'Pure', 'Impure']
        }

    def test_price_calculator_calculate_success(self):
        """Tests the full calculation workflow with valid data and verifies the 'Total' column and timezone."""
        df_to_test = pd.DataFrame(self.sample_df_data.copy())
        calculator = PriceCalculator(df_to_test)
        result_df = calculator.calculate()

        # Define expected total values based on the business logic
        expected_total = pd.Series([1000.0, 750.0, 400.0, 112.5], name='Total')
        pd.testing.assert_series_equal(result_df['Total'], expected_total, check_dtype=False)

        # Verify datetime column's timezone and hour after conversion
        self.assertEqual(str(result_df['Datetime'].dtype), 'datetime64[ns, Etc/GMT-6]')
        self.assertEqual(result_df['Datetime'].iloc[0].tz_convert('UTC').hour, 10)


    def test_price_calculator_serialize_data(self):
        """Tests that the 'Datetime' column is correctly converted to datetime objects."""
        df_copy = pd.DataFrame(self.sample_df_data.copy())
        calculator = PriceCalculator(df_copy)
        calculator._serialize_data()
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(calculator.df['Datetime']))

    def test_price_calculator_validate_missing_columns(self):
        """Tests that a ValueError is raised if a required column is missing."""
        df_missing_col = pd.DataFrame(self.sample_df_data.copy()).drop(columns=['Price'])
        calculator = PriceCalculator(df_missing_col)
        with self.assertRaisesRegex(ValueError, "Missing required columns: Price."):
            calculator._validate_data()

    def test_price_calculator_validate_null_values(self):
        """Tests that a ValueError is raised if the DataFrame contains any null values."""
        df_with_null = pd.DataFrame(self.sample_df_data.copy())
        df_with_null.loc[0, 'Amount'] = np.nan # Introduce a null value
        calculator = PriceCalculator(df_with_null)
        with self.assertRaisesRegex(ValueError, "The dataframe contains null values."):
            calculator._validate_data()

    def test_price_calculator_validate_non_numeric_amount(self):
        """Tests that a ValueError is raised if the 'Amount' column is not numeric."""
        df_non_numeric = pd.DataFrame(self.sample_df_data.copy())
        df_non_numeric['Amount'] = ['10', '5', '20', '15'] # Non-numeric data
        calculator = PriceCalculator(df_non_numeric)
        with self.assertRaisesRegex(ValueError, "Amount and price are not numeric."):
            calculator._validate_data()

    def test_price_calculator_validate_non_numeric_price(self):
        """Tests that a ValueError is raised if the 'Price' column is not numeric."""
        df_non_numeric = pd.DataFrame(self.sample_df_data.copy())
        df_non_numeric['Price'] = ['100', '200', '120', '210'] # Non-numeric data
        calculator = PriceCalculator(df_non_numeric)
        with self.assertRaisesRegex(ValueError, "Amount and price are not numeric."):
            calculator._validate_data()

    def test_price_calculator_validate_non_string_name(self):
        """Tests that a ValueError is raised if the 'Name' column is not a string."""
        df_non_string = pd.DataFrame(self.sample_df_data.copy())
        df_non_string['Name'] = [1, 2, 3, 4] # Non-string data
        calculator = PriceCalculator(df_non_string)
        with self.assertRaisesRegex(ValueError, "Name column is not a string."):
            calculator._validate_data()

    def test_price_calculator_validate_duplicate_producta_timestamp(self):
        """
        Tests that a ValueError is raised if Product A has duplicate timestamps.
        Uses a temporary file to simulate the scenario.
        """
        with tempfile.TemporaryDirectory() as tmp_path_for_dup:
            source_file = os.path.join(tmp_path_for_dup, "source_dup.csv")

            df_dup_producta = pd.DataFrame({
                'Name': ['ProductA', 'ProductA', 'ProductB'],
                'Datetime': ['2023-01-01 10:00:00', '2023-01-01 10:00:00', '2023-01-01 10:00:00'],
                'Amount': [10, 5, 20],
                'Price': [100, 150, 120],
                'Purity': ['Pure', 'Pure', 'Pure']
            })
            df_dup_producta.to_csv(source_file, index=False)

            handler = DataHandler(DataSourceType.FILE, str(source_file), "")
            df_to_calculate = handler.retrieve_df()

            calculator = PriceCalculator(df_to_calculate)
            calculator._serialize_data()
            with self.assertRaisesRegex(ValueError, "Product A has duplicate timestamps"):
                calculator._validate_data()

    def test_price_calculator_update_timezone(self):
        """Tests that the 'Datetime' column's timezone is correctly converted to 'Etc/GMT-6'."""
        df_copy = pd.DataFrame(self.sample_df_data.copy())
        calculator = PriceCalculator(df_copy)
        calculator._serialize_data()
        calculator._update_timezone()

        self.assertEqual(str(calculator.df['Datetime'].dtype), 'datetime64[ns, Etc/GMT-6]')
        # Verify the hour remains consistent after conversion to UTC and then checking its hour
        self.assertEqual(calculator.df['Datetime'].iloc[0].tz_convert('UTC').hour, 10)


    def test_price_calculator_calculate_total_logic(self):
        """
        Tests the _calculate_total method with various scenarios, covering all
        Product A/B and Pure/Impure purity combinations.
        """
        df = pd.DataFrame({
            'Name': ['ProductA', 'ProductA', 'ProductB', 'ProductB', 'ProductA'],
            'Datetime': [
                '2023-01-01 10:00:00', '2023-01-01 11:00:00',
                '2023-01-01 10:00:00', '2023-01-01 11:00:00',
                '2023-01-01 12:00:00'
            ],
            'Amount': [10, 5, 20, 15, 8],
            'Price': [100, 200, 120, 210, 300],
            'Purity': ['Pure', 'Impure', 'Pure', 'Impure', 'Pure']
        })

        # Pre-process datetime column as _calculate_total expects this
        df['Datetime'] = pd.to_datetime(df['Datetime']).dt.tz_localize('UTC').dt.tz_convert('Etc/GMT-6')

        calculator = PriceCalculator(df)
        calculator._calculate_total()

        # Expected 'Total' values based on the defined business logic
        expected_total = pd.Series([1000.0, 750.0, 400.0, 112.5, 2400.0], name='Total')
        pd.testing.assert_series_equal(calculator.df['Total'], expected_total, check_dtype=False)


if __name__ == '__main__':
    # Allows the test file to be run directly from the command line.
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
