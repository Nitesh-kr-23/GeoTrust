import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import create_engine

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    db_url = DATABASE_URL
else:
    db_path = os.environ.get(
        "GEOTRUST_DB_PATH",
        os.path.join(os.path.dirname(__file__), "..", "backend", "geotrust.db"),
    )
    db_url = f"sqlite:///{db_path}"

engine = create_engine(db_url)

st.set_page_config(page_title="GeoTrust Analytics", layout="wide")
st.title("GeoTrust — Vendor & Demand Analytics")
_db_kind = "PostgreSQL" if db_url.startswith("postgresql") else "SQLite"
st.caption(f"Reads live from the same database the API writes to ({_db_kind}).")

try:
    shops_df = pd.read_sql("SELECT * FROM shops", engine)
    logs_df = pd.read_sql("SELECT * FROM search_logs", engine)
    bookings_df = pd.read_sql("SELECT * FROM bookings", engine)
except Exception as e:
    st.warning(f"No data yet — run a few searches through the app first. ({e})")
    st.stop()

if shops_df.empty:
    st.info("No shops cached yet. Search for something in the main app first.")
    st.stop()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Shops indexed", len(shops_df))
col2.metric("Categories covered", shops_df["category"].nunique())
col3.metric("Searches logged", len(logs_df))
col4.metric("Bookings made", len(bookings_df))

st.divider()

# --- Vendor benchmark scorecard ---
st.subheader("Vendor benchmark scorecard")
st.caption("Trust score vs. star rating — shops above the diagonal have a trust score "
           "the raw rating alone wouldn't predict (e.g. rating propped up by very few reviews).")

fig1, ax1 = plt.subplots(figsize=(6, 4))
ax1.scatter(shops_df["rating"], shops_df["trust_score"], alpha=0.6, c="#c8622e")
ax1.plot([1, 5], [0.2, 1.0], linestyle="--", color="#999", linewidth=1)  # rough reference line
ax1.set_xlabel("Google star rating")
ax1.set_ylabel("GeoTrust trust score")
ax1.set_xlim(1, 5)
ax1.set_ylim(0, 1)
st.pyplot(fig1)

st.dataframe(
    shops_df[["name", "category", "rating", "user_ratings_total", "trust_score", "avg_sentiment"]]
    .sort_values("trust_score", ascending=False),
    use_container_width=True,
)

st.divider()

# --- Demand-supply gap ---
st.subheader("Demand vs. supply by category")
st.caption("Search volume (demand signal) vs. number of indexed shops (supply) per category.")

if not logs_df.empty:
    demand = logs_df.groupby("category").size().rename("searches")
    supply = shops_df.groupby("category").size().rename("shops_indexed")
    gap_df = pd.concat([demand, supply], axis=1).fillna(0)
    gap_df["demand_per_shop"] = gap_df["searches"] / gap_df["shops_indexed"].replace(0, 1)
    st.bar_chart(gap_df[["searches", "shops_indexed"]])
    st.dataframe(gap_df.sort_values("demand_per_shop", ascending=False), use_container_width=True)
else:
    st.info("No search logs yet — run some searches to populate this chart.")

st.divider()

# --- Simple map view ---
st.subheader("Indexed shop locations")
map_df = shops_df.rename(columns={"latitude": "lat", "longitude": "lon"})[["lat", "lon"]]
st.map(map_df, size=20)
