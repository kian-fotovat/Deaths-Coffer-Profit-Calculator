import math

import pandas as pd
import requests
import streamlit as st

# Configuration
API_URL = "https://api.deaths-coffer.com/calculate/deathsCoffer"
BASE_URL = "https://api.deaths-coffer.com"

# Items to exclude from the results since they are not sacrificeable
# Needs to be expanded to include additional items (e.g. Grid Master rewards)
EXCLUDED_ITEMS = {
    "Shattered cannon ornament kit",
    "Shattered relics variety ornament kit",
    "Trailblazer tool ornament kit",
    "Trailblazer rug",
    "Shattered hood (t2)",
    "Shattered top (t2)",
    "Shattered trousers (t2)",
    "Shattered boots (t2)",
    "Echo ahrim's ornament kit",
    "Echo virtus ornament kit",
    "Contract of catalyst acquisition",
    "Contract of worm acquisition",
    "Contract of shard acquisition",
    "Contract of oathplate acquisition",
    "Contract of harmony acquisition",
    "Contract of forfeit breath",
    "Contract of glyphic attenuation",
    "Contract of sensory clouding",
    "Contract of divine severance",
    "Contract of bloodied blows",
    "Contract of familiar acquisition",
    "Demonic tallow",
    "Soulflame Horn",
    "Oathplate armour",
    "Twisted coat (t3)",
    "Chasm teleport scroll",
    "Sun-kissed bones",
    "Spirit seed",
}


def fetch_data():
    """
    Fetches data from the Death's Coffer API.
    """
    payload = {
        "minimumOfferingValue": 100000,
        "maximumPrice": None,
        "minimumTradeVolume": 1,
    }
    try:
        response = requests.post(API_URL, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
        items = [item for item in data.get("bestOfferings", []) if item.get("name") not in EXCLUDED_ITEMS]
        return items
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data from API: {e}")
        return []


def main():
    """
    Main function to run the Streamlit application.
    """
    st.set_page_config(page_title="Death's Coffer Profit Calculator", layout="wide")

    st.title("Death's Coffer Profit Calculator")
    st.markdown("The API returns the most profitable items to offer. Use the controls below to sort and filter these results.")

    items = fetch_data()

    if not items:
        st.warning("No items to display.")
        return

    df = pd.DataFrame(items)

    # Drop id and iconPath columns
    df = df.drop(columns=["id", "iconPath"])

    # Sort by ROI by default before applying filters
    if "roi" in df.columns:
        df = df.sort_values(by="roi", ascending=False).reset_index(drop=True)

    # Sidebar for Filtering
    st.sidebar.header("Filter Options")

    # Text search for name
    name_search = st.sidebar.text_input("Search by Name")
    if name_search:
        df = df[df["name"].str.contains(name_search, case=False, regex=False)]

    # Numeric range filters
    def add_range_filter(column_name, display_name, default_min=None):
        if column_name not in df.columns:
            return df

        st.sidebar.subheader(f"{display_name}")
        try:
            min_col_val = math.floor(df[column_name].min())
        except (ValueError, TypeError):
            min_col_val = 0
        try:
            max_col_val = math.ceil(df[column_name].max())
        except (ValueError, TypeError):
            max_col_val = 9999999999

        min_val_default = default_min if default_min is not None else min_col_val
        max_val_default = max_col_val

        col1, col2 = st.sidebar.columns(2)
        min_val = col1.number_input("Min", value=min_val_default, key=f"min_{column_name}")
        max_val = col2.number_input("Max", value=max_val_default, key=f"max_{column_name}")

        return df[(df[column_name] >= min_val) & (df[column_name] <= max_val)]

    df = add_range_filter("grandExchangeGuidePrice", "GE Price")
    df = add_range_filter("buyPrice", "Buy Price")
    df = add_range_filter("sellPrice", "Sell Price")
    df = add_range_filter("deathsCofferValue", "Coffer Value")
    df = add_range_filter("priceDifference", "Profit")
    df = add_range_filter("roi", "ROI (%)")
    df = add_range_filter("tradeVolume", "Trade Volume")
    df = add_range_filter("tradeLimit", "Trade Limit")
    df = add_range_filter("maxOfferingValue", "Max Offering Value")

    # Formatting for Display
    df_display = df.copy()

    COLUMN_MAPPING = {
        "name": "Name",
        "grandExchangeGuidePrice": "GE Price",
        "buyPrice": "Buy Price",
        "sellPrice": "Sell Price",
        "deathsCofferValue": "Coffer Value",
        "priceDifference": "Profit",
        "roi": "ROI (%)",
        "tradeVolume": "Trade Volume",
        "tradeLimit": "Trade Limit",
        "maxOfferingValue": "Max Offering Value",
        "lastGrandExchangeUpdate": "Last GE Update",
        "lastRuneLiteUpdate": "Last RuneLite Update",
    }
    df_display.rename(columns=COLUMN_MAPPING, inplace=True)

    # Format datetime columns to be more readable
    for col_name in ["Last GE Update", "Last RuneLite Update"]:
        if col_name in df_display.columns:
            timestamp = pd.to_datetime(df_display[col_name], errors="coerce")
            try:
                converted_timestamps = timestamp.dt.tz_convert("US/Central")
            except TypeError:
                converted_timestamps = timestamp.dt.tz_localize("UTC")
                converted_timestamps = converted_timestamps.dt.tz_convert("US/Central")
            df_display[col_name] = converted_timestamps.dt.strftime("%m/%d/%Y, %I:%M %p")

    # Define numeric columns using their original names
    numeric_columns_original = ["grandExchangeGuidePrice", "buyPrice", "sellPrice", "deathsCofferValue", "priceDifference", "tradeVolume", "tradeLimit", "maxOfferingValue"]
    numeric_columns_renamed = [COLUMN_MAPPING.get(col, col) for col in numeric_columns_original]
    format_dict = {col: "{:,.0f}" for col in numeric_columns_renamed if col in df_display.columns}

    if "ROI (%)" in df_display.columns:
        format_dict["ROI (%)"] = "{:,.2f}%"

    # Reorder columns for a more logical display
    display_columns = [
        "Name",
        "ROI (%)",
        "Profit",
        "GE Price",
        "Buy Price",
        "Sell Price",
        "Coffer Value",
        "Max Offering Value",
        "Trade Volume",
        "Trade Limit",
        "Last GE Update",
        "Last RuneLite Update",
    ]

    # Filter columns to only those that exist in the dataframe
    df_display = df_display[display_columns]

    # Display DataFrame with Styling
    styler = df_display.style.format(format_dict)
    st.dataframe(styler, width="stretch", height=1000)


if __name__ == "__main__":
    main()
