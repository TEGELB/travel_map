from typing import Optional, Dict
from datetime import timedelta

import pandas as pd
import plotly.graph_objects as go
import plotly.colors as pc
from plotly.colors import sample_colorscale


def get_rgb_from_scale(value: float, colorscale: str) -> tuple:
    """
    Convert a normalized value (0-1) into an RGB tuple using the given Plotly colorscale.

    Parameters:
        value (float): Normalized value between 0 and 1.
        colorscale (str): Name of the Plotly color scale.

    Returns:
        tuple: (r, g, b)
    """
    # Ensure value is in [0, 1]
    value = max(0, min(1, value))
    rgb_string = pc.find_intermediate_color(
        pc.get_colorscale(colorscale)[0][1],
        pc.get_colorscale(colorscale)[-1][1],
        value,
        colortype="rgb"
    )
    return tuple(int(x) for x in rgb_string.strip("rgb()").split(","))


def midpoint_rgb(color1: str, color2: str, alpha: float = 1.0) -> str:
    """
    Compute the midpoint RGBA color string between two RGB strings.

    Parameters:
        color1 (str): RGB color string, e.g., 'rgb(255, 100, 0)'
        color2 (str): RGB color string
        alpha (float): Alpha (opacity) value for the output RGBA string

    Returns:
        str: RGBA color string
    """

    def rgb_str_to_tuple(rgb_str):
        return tuple(int(c.strip()) for c in rgb_str.strip("rgb() ").split(","))

    rgb1 = rgb_str_to_tuple(color1)
    rgb2 = rgb_str_to_tuple(color2)
    mid_rgb = tuple((a + b) // 2 for a, b in zip(rgb1, rgb2))

    return f"rgba({mid_rgb[0]}, {mid_rgb[1]}, {mid_rgb[2]}, {alpha})"

def build_continuous_scale(hex_colors):
    """Convert hex color list to Plotly continuous color scale format."""
    n = len(hex_colors)
    return [[i / (n - 1), color] for i, color in enumerate(hex_colors)]

def build_colored_lines_geo(df_sorted, lat_col, lon_col, date_range, color_scale, width=2, line_opacity=0.8, **kwargs):
    """
    Builds a list of Scattergeo line traces colored by the midpoint of a colorscale.

    Parameters:
        df_sorted (pd.DataFrame): Sorted DataFrame with lat/lon columns.
        lat_col (str): Name of the latitude column.
        lon_col (str): Name of the longitude column.
        date_range (pd.Series): Normalized values (0 to 1) for the colorscale.
        color_scale (list): Plotly-compatible colorscale.
        line_opacity (float): Line opacity for RGBA colors.
        width (int): width of the plotted lines
        **kwargs: Additional arguments to pass to go.Scattergeo (e.g. name, hoverinfo).

    Returns:
        list: List of plotly.graph_objects.Scattergeo traces.
    """
    lines = []

    for i in range(len(df_sorted) - 1):
        lat0, lon0 = df_sorted.loc[i, [lat_col, lon_col]]
        lat1, lon1 = df_sorted.loc[i + 1, [lat_col, lon_col]]

        norm0 = date_range.iloc[i]
        norm1 = date_range.iloc[i + 1]

        rgb0 = sample_colorscale(color_scale, norm0, colortype='rgb')[0]
        rgb1 = sample_colorscale(color_scale, norm1, colortype='rgb')[0]

        rgba_color = midpoint_rgb(rgb0, rgb1, alpha=line_opacity)

        lines.append(go.Scattergeo(
            lat=[lat0, lat1],
            lon=[lon0, lon1],
            mode="lines",
            line=dict(width=width, color=rgba_color),
            opacity=line_opacity,
            **kwargs
        ))

    return lines

def plot_travel_map(
    df: pd.DataFrame,
    lat_col: str = "Latitude",
    lon_col: str = "Longitude",
    city_col: str = "City",
    duration_col: str = "Duration",
    date_col: str = "Start",
    default_marker_size: int = 5,
    marker_scale: float = 2.0,
    color_scale: str = "Viridis",
    line_opacity: float = 0.6,
    location_name: str = "Cities",
    city_marker_kwargs: Optional[Dict] = None,
    line_kwargs: Optional[Dict] = None,
    plot_kwargs: Optional[Dict] = None
) -> go.Figure:
    """
    Plots a world map of visited cities with size based on duration and color based on entry date.

    Parameters:
        df (pd.DataFrame): DataFrame with geolocation and visit data.
        lat_col (str): Name of the latitude column.
        lon_col (str): Name of the longitude column.
        city_col (str): Name of the city column.
        duration_col (str): Name of the duration column.
        date_col (str): Name of the entry date column (should be datetime).
        default_marker_size (int): Minimum size for markers.
        marker_scale (float): Scaling factor for marker size.
        color_scale (str): Color scale name for Plotly.
        line_opacity (float): Opacity of the lines connecting cities.
        location_name (string): Name for the Location plots
        city_marker_kwargs (dict): Extra kwargs for the Scattergeo markers.
        line_kwargs (dict): Extra kwargs for the lines (passed to build_colored_lines_geo).
        plot_kwargs (dict): Extra kwargs for the go.Figure/layout.

    Returns:
        go.Figure: The resulting Plotly figure.
    """

    # ---------- Default configurations ----------
    default_city_marker_kwargs = dict(
        colorbar=dict(title="Date"),
        line=dict(width=0.5, color="black")
    )

    default_line_kwargs = dict(
        showlegend=False,
        width=2,
        lat_col="Latitude",
        lon_col="Longitude",
    )

    default_plot_kwargs = dict(
        geo=dict(
            projection_type="natural earth",
            showland=True,
            landcolor="rgb(243, 243, 243)",
            showcountries=True,
            countrycolor="rgb(204, 204, 204)",
            fitbounds="locations"
        ),
        title="Travel Map",
        margin=dict(l=0, r=0, t=40, b=0)
    )

    # ---------- Apply user overrides ----------
    city_kwargs = {**default_city_marker_kwargs, **(city_marker_kwargs or {})}
    line_kwargs = {**default_line_kwargs, **(line_kwargs or {})}
    plot_kwargs = {**default_plot_kwargs, **(plot_kwargs or {})}

    df_sorted = df.sort_values(by=date_col).reset_index(drop=True)

    # Normalize date to float for coloring
    date_min = df_sorted[date_col].min()
    date_max = df_sorted[date_col].max()
    date_range = (df_sorted[date_col] - date_min) / (date_max - date_min + pd.Timedelta(days=1e-9))

    # Compute marker size and color
    sizes = df_sorted[duration_col].fillna(1) * marker_scale + default_marker_size

    # Create scatter trace for cities
    scatter = go.Scattergeo(
        lat=df_sorted[lat_col],
        lon=df_sorted[lon_col],
        text=[f"{row[city_col]}<br>{row[date_col].strftime('%d.%m.%Y')} - {(row[date_col]+timedelta(days=row[duration_col])).strftime('%d.%m.%Y')}:  {row[duration_col]} days" for _, row in df_sorted.iterrows()],
        mode="markers",
        marker=dict(
            size=sizes,
            color=date_range,
            colorscale=color_scale,
            opacity=line_opacity,
            **city_kwargs
        ),
        name=location_name
    )

    lines = build_colored_lines_geo(
        df_sorted=df_sorted,
        date_range=date_range,
        color_scale=color_scale,
        line_opacity=line_opacity,
        **line_kwargs
    )

    fig = go.Figure([scatter] + lines)

    fig.update_layout(
        **plot_kwargs
    )

    return fig