"""
This code follows the Single Responsibility and Open/Closed principles;
each class has its own purpose, and each method perform a single, discrete operation
"""

import enum
import logging
import os
import sys

import numpy as np
import pandas as pd

from pandas.core.dtypes.common import is_string_dtype, is_numeric_dtype


logger = logging.getLogger(__name__)


class DataSourceType(enum.Enum):
    """
    There can be multiple data sources: file (in this case), database request, API call, etc.
    """
    FILE = "file"
    DATABASE = "database"
    API = "api"


class DataHandler:
    """
    Imports/exports dataframe from/to multiple data sources: file (in this case), database request, API call, etc.
    """

    MAX_FILE_SIZE_GB = 2

    def __init__(self, data_source_type: DataSourceType, path_import: str, path_export: str) -> None:
        self.data_source_type: DataSourceType = data_source_type
        self.path_import: str = path_import
        self.path_export: str = path_export
        logger.info(f"DataHandler initialized for source type: {data_source_type.value}")
        logger.info(f"Import path: {path_import}, Export path: {path_export}")


    def retrieve_df(self) -> pd.DataFrame:
        logger.info(f"Attempting to retrieve dataframe from {self.data_source_type.value}")
        if self.data_source_type == DataSourceType.FILE:
            return self._read_file()
        elif self.data_source_type == DataSourceType.DATABASE:
            return self._query_database()
        elif self.data_source_type == DataSourceType.API:
            return self._fetch_api()
        raise NotImplementedError('Such a data source is not implemented')

    def _read_file(self) -> pd.DataFrame:
        logger.info(f"Reading file from: {self.path_import}")
        file_size_gb = os.path.getsize(self.path_import) / (1024*1024*1024)
        if file_size_gb > self.MAX_FILE_SIZE_GB:
            raise ValueError(
                f"File is too large. Maximum allowed size is {self.MAX_FILE_SIZE_GB}. Use database instead."
            )

        df = pd.read_csv(self.path_import)
        logger.info(f"Successfully read {len(df)} rows from {self.path_import}")
        return df

    def _query_database(self) -> pd.DataFrame:
        raise NotImplementedError('Database query is not implemented')

    def _fetch_api(self) -> pd.DataFrame:
        raise NotImplementedError('API fetch is not implemented')

    def export_df(self, df: pd.DataFrame) -> None:
        logger.info(f"Attempting to export dataframe to {self.data_source_type.value}")
        if self.data_source_type == DataSourceType.FILE:
            self._export_to_file(df)
        elif self.data_source_type == DataSourceType.DATABASE:
            self._save_to_database(df)
        elif self.data_source_type == DataSourceType.API:
            self._post_data(df)
        else:
            raise NotImplementedError('Such a data source is not implemented')

    def _export_to_file(self, df: pd.DataFrame) -> None:
        logger.info(f"Exporting dataframe to file: {self.path_export}")
        df.to_csv(self.path_export, index=False)
        logger.info(f"Successfully exported {len(df)} rows to {self.path_export}")

    def _save_to_database(self, df: pd.DataFrame) -> None:
        raise NotImplementedError('Database save is not implemented')

    def _post_data(self, df: pd.DataFrame) -> None:
        raise NotImplementedError('API post is not implemented')


class PriceCalculator:
    """
    Calculates (using vectors without slow apply method as a bad practice) and rounds total prices in validated dataframe.
    Public method calculate() includes private methods with steps of serialization, validation and calculation.
    """

    def __init__(self, df: pd.DataFrame) -> None:
        self.df: pd.DataFrame = df
        logger.info("PriceCalculator initialized.")

    def calculate(self, round_precision: int = 2) -> pd.DataFrame:
        logger.info("Starting price calculation process.")
        self._serialize_data()
        self._validate_data()
        self._update_timezone()
        self._calculate_total()
        self._round_total(round_precision=round_precision)
        logger.info("Price calculation process completed successfully.")
        return self.df

    def _serialize_data(self) -> None:
        logger.info("Serializing 'Datetime' column to datetime objects.")
        self.df['Datetime'] = pd.to_datetime(self.df['Datetime'])

    def _validate_data(self) -> None:
        logger.info("Validating data.")
        # Validation for missing columns required for the task in the dataframe
        list_of_required_columns = ['Name', 'Datetime', 'Amount', 'Price', 'Purity']
        missing = [col for col in list_of_required_columns if col not in self.df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(missing)}. ")

        if self.df.isnull().values.any():
            raise ValueError('The dataframe contains null values.')

        if not is_numeric_dtype(self.df['Amount']) or not is_numeric_dtype(self.df['Price']):
            raise ValueError('Amount and price are not numeric.')
        if not is_string_dtype(self.df['Name']):
            raise ValueError('Name column is not a string.')

        # From the 'Step 3' of the task it is logical that a product should have a single price at a given timestamp
        duplicates_count = self.df[self.df['Name'] == 'ProductA'].duplicated(subset=['Datetime']).sum()
        if duplicates_count > 0:
             raise ValueError('Product A has duplicate timestamps')
        logger.info("Data validation passed.")

    def _update_timezone(self) -> None:
        """
        Convert values in datetime column from timezone UTC to UTC+6
        """
        logger.info("Updating timezone to 'Etc/GMT-6'.")
        if self.df['Datetime'].dt.tz is not None:
            self.df['Datetime'] = self.df['Datetime'].dt.tz_convert('UTC').dt.tz_convert('Etc/GMT-6')
        else:
            self.df['Datetime'] = self.df['Datetime'].dt.tz_localize('UTC').dt.tz_convert('Etc/GMT-6')

    def _calculate_total(self) -> None:
        """
        Add new column - total - where:
        Product A is an outright and, if product purity is 'Pure', the total should therefore be calculated as amount * price
        Product B is a diff and the total should be found by taking its respective Product A price (the one with matching timestamp) from the price of Product B given, before multiplying by the amount of Product B
        If the Product purity is 'Impure' prices should be reduced to 3/4 of its given value when calculating the total

        Implementation via np.select (more efficient)
        Alternative implementation: LEFT JOIN on datetime and calculating difference between price columns
        """
        logger.info("Calculating 'Total' column.")
        conditions: list = [
            (self.df['Name'] == 'ProductA') & (self.df['Purity'] == 'Pure'),
            (self.df['Name'] == 'ProductA') & (self.df['Purity'] == 'Impure'),
            (self.df['Name'] == 'ProductB') & (self.df['Purity'] == 'Pure'),
            (self.df['Name'] == 'ProductB') & (self.df['Purity'] == 'Impure'),
        ]

        # Creating series of Product A with Datetime as index
        product_a_series: pd.Series = self.df[self.df['Name'] == 'ProductA'].set_index('Datetime')['Price']
        # Maps prices of Product B and Product A based on the same timestamp and calculates the difference
        price_difference: pd.Series = self.df['Price'] - self.df['Datetime'].map(product_a_series)
        results: list = [
            self.df['Price'] * self.df['Amount'],
            self.df['Price'] * 0.75 * self.df['Amount'],
            price_difference * self.df['Amount'],
            price_difference * 0.75 * self.df['Amount'],
        ]
        self.df['Total'] = np.select(
            conditions, results, default=np.nan
        )
        logger.info("Calculation of 'Total' column complete.")

    def _round_total(self, round_precision: int) -> None:
        logger.info(f"Rounding 'Total' column to {round_precision} decimal places.")
        if not isinstance(round_precision, int):
            raise TypeError(
                f"Rounding precision must be an integer, but got {type(round_precision).__name__}."
            )
        self.df['Total'] = self.df['Total'].round(round_precision)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout,
    )

    logger.info("Script started.")

    data_handler: DataHandler = DataHandler(
        data_source_type=DataSourceType.FILE,
        path_import='source.csv',
        path_export='result.csv',)

    # Load csv data from source.csv file
    df_to_calculate: pd.DataFrame = data_handler.retrieve_df()

    price_calculator: PriceCalculator = PriceCalculator(df=df_to_calculate)
    df_total:pd.DataFrame = price_calculator.calculate()

    # Save the result to the new file result.csv
    data_handler.export_df(df=df_total)

    logger.info("Script finished.")