import enum
import os

import numpy as np
import pandas as pd

from pandas.core.dtypes.common import is_string_dtype, is_numeric_dtype



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

    def retrieve_df(self) -> pd.DataFrame:
        if self.data_source_type == DataSourceType.FILE:
            return self._read_file()
        elif self.data_source_type == DataSourceType.DATABASE:
            return self._query_database()
        elif self.data_source_type == DataSourceType.API:
            return self._fetch_api()
        raise NotImplementedError('Such a data source is not implemented')

    def _read_file(self) -> pd.DataFrame:
        file_size_gb = os.path.getsize(self.path_import) / (1024*1024*1024)
        if file_size_gb > self.MAX_FILE_SIZE_GB:
            raise ValueError(
                f"File is too large. Maximum allowed size is {self.MAX_FILE_SIZE_GB}. Use database instead."
            )
        return pd.read_csv(self.path_import)

    def _query_database(self) -> pd.DataFrame:
        raise NotImplementedError('Database query is not implemented')

    def _fetch_api(self) -> pd.DataFrame:
        raise NotImplementedError('API fetch is not implemented')

    def export_df(self, df: pd.DataFrame) -> None:
        if self.data_source_type == DataSourceType.FILE:
            self._export_to_file(df)
        elif self.data_source_type == DataSourceType.DATABASE:
            self._save_to_database(df)
        elif self.data_source_type == DataSourceType.API:
            self._post_data(df)
        else:
            raise NotImplementedError('Such a data source is not implemented')

    def _export_to_file(self, df: pd.DataFrame) -> None:
        df.to_csv(self.path_export, index=False)

    def _save_to_database(self, df: pd.DataFrame) -> None:
        raise NotImplementedError('Database save is not implemented')

    def _post_data(self, df: pd.DataFrame) -> None:
        raise NotImplementedError('API post is not implemented')


class PriceCalculator:
    """
    Calculate total prices in validated dataframe.
    Public method calculate() includes private methods with steps of serialization, validation and calculation.
    """

    def __init__(self, df: pd.DataFrame) -> None:
        self.df: pd.DataFrame = df

    def calculate(self) -> pd.DataFrame:
        self._serialize_data()
        self._validate_data()
        self._update_timezone()
        self._calculate_total()
        return self.df

    def _serialize_data(self) -> None:
        self.df['Datetime'] = pd.to_datetime(self.df['Datetime'])

    def _validate_data(self) -> None:
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

    def _update_timezone(self) -> None:
        """
        Convert values in datetime column from timezone UTC to UTC+6
        """
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
