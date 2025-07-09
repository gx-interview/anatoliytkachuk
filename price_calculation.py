import enum
import os

import pandas as pd



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


