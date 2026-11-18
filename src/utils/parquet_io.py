"""
Utility for saving and reading Parquet files cleanly.
Uses PyArrow when available, with automatic DuckDB fallback.
"""

from pathlib import Path
import pandas as pd

try:
    import pyarrow
    _HAS_PYARROW = True
except ImportError:
    _HAS_PYARROW = False

try:
    import duckdb
    _HAS_DUCKDB = True
except ImportError:
    _HAS_DUCKDB = False


def save_parquet(df: pd.DataFrame, dest_path: Path):
    """Save dataframe to Parquet using PyArrow or DuckDB engine."""
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    if _HAS_PYARROW:
        df.to_parquet(str(dest_path), index=False, engine="pyarrow")
    elif _HAS_DUCKDB:
        # Use DuckDB for zero-dependency high-speed Parquet serialization
        con = duckdb.connect()
        con.register("df_view", df)
        con.execute(f"COPY df_view TO '{dest_path.as_posix()}' (FORMAT PARQUET, COMPRESSION SNAPPY)")
        con.close()
    else:
        # Fallback to pandas default
        df.to_parquet(str(dest_path), index=False)


def read_parquet(source_path: Path) -> pd.DataFrame:
    """Read Parquet into a Pandas DataFrame."""
    source_path = Path(source_path)
    if _HAS_PYARROW:
        return pd.read_parquet(str(source_path), engine="pyarrow")
    elif _HAS_DUCKDB:
        con = duckdb.connect()
        df = con.execute(f"SELECT * FROM read_parquet('{source_path.as_posix()}')").fetchdf()
        con.close()
        return df
    else:
        return pd.read_parquet(str(source_path))
