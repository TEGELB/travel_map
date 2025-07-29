import pandas as pd
from typing import Optional

def summarize_travel(df: pd.DataFrame, column_map: dict = None, show_total: bool = True) -> pd.DataFrame:
    """
    Summarizes travel statistics per country:
    - Total duration (sum of days)
    - Number of unique cities visited
    - First date of entry
    - Last date of exit
    - (Optional) Total row with overall stats

    Parameters:
        df (pd.DataFrame): The travel DataFrame returned by parse_markdown.
        column_map (dict): Optional mapping of DataFrame column names.
        show_total (bool): Whether to include a final row with totals.

    Returns:
        pd.DataFrame: Summary table with optional total row.
    """
    default_columns = {
        "country": "Country",
        "city": "City",
        "duration": "Duration",
        "start": "Start",
        "end": "End"
    }

    columns = column_map if column_map else default_columns

    summary = df.groupby(columns["country"]).agg(
        Total_Days=(columns["duration"], "sum"),
        Cities_Visited=(columns["city"], pd.Series.nunique),
        Entry_Date=(columns["start"], "min"),
        Exit_Date=(columns["end"], "max")
    ).reset_index()

    # Sort by Entry_Date
    summary = summary.sort_values(by="Entry_Date").reset_index(drop=True)

    if show_total:
        total_row = {
            columns["country"]: "TOTAL",
            "Total_Days": summary["Total_Days"].sum(),
            "Cities_Visited": summary["Cities_Visited"].sum(),
            "Entry_Date": summary["Entry_Date"].min(),
            "Exit_Date": summary["Exit_Date"].max()
        }
        summary = pd.concat([summary, pd.DataFrame([total_row])], ignore_index=True)

    return summary

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable, GeocoderTimedOut
import time

def map_cities_to_coords(df: pd.DataFrame, city_col="City", country_col="Country", user_agent="city-geocoder", api_wait_time=0.1) -> pd.DataFrame:
    """
    Adds 'Latitude' and 'Longitude' columns to the DataFrame by geocoding city and country.
    If a city cannot be geocoded, sets both to None.

    Parameters:
        df (pd.DataFrame): Input DataFrame with city and country columns.
        city_col (str): Name of the column containing city names.
        country_col (str): Name of the column containing country names.
        user_agent (str): Identifier for the Nominatim geocoder.

    Returns:
        pd.DataFrame: DataFrame with additional 'Latitude' and 'Longitude' columns.
        :param api_wait_time:
    """
    geolocator = Nominatim(user_agent=user_agent)
    latitudes, longitudes = [], []

    for _, row in df.iterrows():
        location_str = f"{row[city_col]}, {row[country_col]}"
        try:
            location = geolocator.geocode(location_str, timeout=10)
            if location:
                latitudes.append(location.latitude)
                longitudes.append(location.longitude)
            else:
                latitudes.append(None)
                longitudes.append(None)
        except (GeocoderTimedOut, GeocoderUnavailable):
            latitudes.append(None)
            longitudes.append(None)
        time.sleep(api_wait_time)  # Be polite to the API

    df["Latitude"] = latitudes
    df["Longitude"] = longitudes
    return df

def get_unmapped_locations(df: pd.DataFrame, lat_col="Latitude", lon_col="Longitude") -> pd.DataFrame:
    """
    Returns a DataFrame of all entries where latitude or longitude is None.

    Parameters:
        df (pd.DataFrame): The DataFrame with geolocation columns.
        lat_col (str): Name of the latitude column.
        lon_col (str): Name of the longitude column.

    Returns:
        pd.DataFrame: Rows where coordinates are missing.
    """
    return df[df[lat_col].isna() | df[lon_col].isna()]

from typing import Union, List

def set_manual_coordinates_by_index(
    df: pd.DataFrame,
    updates: Union[List[Union[int, float]], List[List[Union[int, float]]]],
    lat_col: str = "Latitude",
    lon_col: str = "Longitude"
) -> pd.DataFrame:
    """
    Manually sets latitude and longitude for rows identified by their index.

    Parameters:
        df (pd.DataFrame): DataFrame to update.
        updates (list): Either a single update [index, lat, lon] or a list of such updates.
        lat_col (str): Name of the latitude column.
        lon_col (str): Name of the longitude column.

    Returns:
        pd.DataFrame: Updated DataFrame with manual coordinates set.
    """
    if isinstance(updates[0], (int, float)):
        updates = [updates]  # single update case

    for idx, lat, lon in updates:
        if idx in df.index:
            df.at[idx, lat_col] = lat
            df.at[idx, lon_col] = lon

    return df

def filter_visits(
    df: pd.DataFrame,
    country: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    column_map: dict = None
) -> pd.DataFrame:
    """
    Filters a DataFrame of visit records by country, start date, and/or end date.

    Parameters:
        df (pd.DataFrame): The original DataFrame.
        column_map (dict): mapping for logical column-names; country, city, start, end, duration
        country (str, optional): If provided, filters rows where 'country' matches.
        start_date (str, optional): If provided, filters rows where 'start' is on or after this date (YYYY-MM-DD).
        end_date (str, optional): If provided, filters rows where 'end' is on or before this date (YYYY-MM-DD).

    Returns:
        pd.DataFrame: A filtered copy of the DataFrame.
    """
    # Copy the DataFrame to avoid modifying the original
    df_filtered = df.copy()

    # Default column mapping
    default_columns = {
        "country": "Country",
        "city": "City",
        "start": "Start",
        "end": "End",
        "duration": "Duration"
    }

    if column_map:
        columns = column_map
    else:
        columns = default_columns


    # Convert date columns to datetime for comparison
    df_filtered[columns["start"]] = pd.to_datetime(df_filtered[columns["start"]])
    df_filtered[columns["end"]] = pd.to_datetime(df_filtered[columns["end"]])

    # Apply filters conditionally
    if country:
        df_filtered = df_filtered[df_filtered[columns["country"]] == country]

    if start_date:
        start_date = pd.to_datetime(start_date, dayfirst=True)
        df_filtered = df_filtered[df_filtered[columns["start"]] >= start_date]

    if end_date:
        end_date = pd.to_datetime(end_date, dayfirst=True)
        df_filtered = df_filtered[df_filtered[columns["end"]] <= end_date]

    return df_filtered