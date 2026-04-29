import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Inventory Analysis Dashboard", page_icon="📦", layout="wide")


@st.cache_data
def load_data(uploaded_file=None):
    """Load CSV either from the uploader or from the repository root."""
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_csv("Dummy_data_for_dummy_app.csv")

    expected_cols = [
        "SKU",
        "Location",
        "Category",
        "Quantity",
        "Unit_Value",
        "Total_Inventory_Value",
        "Lead_Time_Days",
        "Storage_Type",
        "Supplier_Region",
        "Criticality",
    ]

    missing = [c for c in expected_cols if c not in df.columns]
    if missing:
        raise ValueError(
            "The CSV is missing these expected columns: " + ", ".join(missing)
        )

    # Type cleanup / coercion
    numeric_cols = ["Quantity", "Unit_Value", "Total_Inventory_Value", "Lead_Time_Days"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["SKU", "Location", "Category", "Storage_Type", "Supplier_Region", "Criticality"]:
        df[col] = df[col].astype(str).str.strip()

    # Useful helper columns for slicing and charting
    criticality_order = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}
    df["Criticality_Score"] = df["Criticality"].map(criticality_order).fillna(0)
    df["Value_per_Unit"] = df["Total_Inventory_Value"] / df["Quantity"].replace(0, pd.NA)

    return df


def apply_filters(df):
    st.sidebar.header("Filters")

    locations = st.sidebar.multiselect(
        "Location", sorted(df["Location"].dropna().unique()), default=sorted(df["Location"].dropna().unique())
    )
    categories = st.sidebar.multiselect(
        "Category", sorted(df["Category"].dropna().unique()), default=sorted(df["Category"].dropna().unique())
    )
    storage_types = st.sidebar.multiselect(
        "Storage Type",
        sorted(df["Storage_Type"].dropna().unique()),
        default=sorted(df["Storage_Type"].dropna().unique()),
    )
    supplier_regions = st.sidebar.multiselect(
        "Supplier Region",
        sorted(df["Supplier_Region"].dropna().unique()),
        default=sorted(df["Supplier_Region"].dropna().unique()),
    )
    criticalities = st.sidebar.multiselect(
        "Criticality",
        sorted(df["Criticality"].dropna().unique()),
        default=sorted(df["Criticality"].dropna().unique()),
    )

    quantity_range = st.sidebar.slider(
        "Quantity range",
        int(df["Quantity"].min()),
        int(df["Quantity"].max()),
        (int(df["Quantity"].min()), int(df["Quantity"].max())),
    )
    lead_time_range = st.sidebar.slider(
        "Lead time range (days)",
        int(df["Lead_Time_Days"].min()),
        int(df["Lead_Time_Days"].max()),
        (int(df["Lead_Time_Days"].min()), int(df["Lead_Time_Days"].max())),
    )
    value_range = st.sidebar.slider(
        "Inventory value range",
        float(df["Total_Inventory_Value"].min()),
        float(df["Total_Inventory_Value"].max()),
        (float(df["Total_Inventory_Value"].min()), float(df["Total_Inventory_Value"].max())),
    )

    filtered = df[
        df["Location"].isin(locations)
        & df["Category"].isin(categories)
        & df["Storage_Type"].isin(storage_types)
        & df["Supplier_Region"].isin(supplier_regions)
        & df["Criticality"].isin(criticalities)
        & df["Quantity"].between(quantity_range[0], quantity_range[1])
        & df["Lead_Time_Days"].between(lead_time_range[0], lead_time_range[1])
        & df["Total_Inventory_Value"].between(value_range[0], value_range[1])
    ].copy()

    return filtered


def display_kpis(df):
    total_value = df["Total_Inventory_Value"].sum()
    total_qty = df["Quantity"].sum()
    sku_count = df["SKU"].nunique()
    avg_lead = df["Lead_Time_Days"].mean() if len(df) else 0
    avg_unit_value = df["Unit_Value"].mean() if len(df) else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Inventory Value", f"${total_value:,.0f}")
    c2.metric("Total Quantity", f"{total_qty:,.0f}")
    c3.metric("Unique SKUs", f"{sku_count}")
    c4.metric("Avg Lead Time", f"{avg_lead:,.1f} days")
    c5.metric("Avg Unit Value", f"${avg_unit_value:,.2f}")


def bar_chart(df, group_col):
    grouped = (
        df.groupby(group_col, dropna=False, as_index=False)["Total_Inventory_Value"]
        .sum()
        .sort_values("Total_Inventory_Value", ascending=False)
    )
    fig = px.bar(
        grouped,
        x=group_col,
        y="Total_Inventory_Value",
        color=group_col,
        text_auto=".2s",
        title=f"Inventory Value by {group_col}",
    )
    fig.update_layout(showlegend=False, yaxis_title="Inventory Value", xaxis_title=group_col)
    return fig


def stacked_chart(df, group_col, color_col):
    grouped = (
        df.groupby([group_col, color_col], dropna=False, as_index=False)["Total_Inventory_Value"]
        .sum()
        .sort_values("Total_Inventory_Value", ascending=False)
    )
    fig = px.bar(
        grouped,
        x=group_col,
        y="Total_Inventory_Value",
        color=color_col,
        title=f"Inventory Value by {group_col} and {color_col}",
    )
    fig.update_layout(barmode="stack", yaxis_title="Inventory Value")
    return fig


def scatter_chart(df):
    fig = px.scatter(
        df,
        x="Lead_Time_Days",
        y="Total_Inventory_Value",
        size="Quantity",
        color="Criticality",
        hover_data=["SKU", "Location", "Category", "Supplier_Region", "Storage_Type"],
        title="Lead Time vs Inventory Value",
    )
    fig.update_layout(xaxis_title="Lead Time (days)", yaxis_title="Inventory Value")
    return fig


def waterfall_chart(df, group_col):
    grouped = (
        df.groupby(group_col, dropna=False, as_index=False)["Total_Inventory_Value"]
        .sum()
        .sort_values("Total_Inventory_Value", ascending=False)
    )

    x_vals = grouped[group_col].astype(str).tolist() + ["Total"]
    y_vals = grouped["Total_Inventory_Value"].tolist() + [grouped["Total_Inventory_Value"].sum()]
    measure = ["relative"] * len(grouped) + ["total"]

    fig = go.Figure(
        go.Waterfall(
            name="Inventory contribution",
            orientation="v",
            measure=measure,
            x=x_vals,
            y=y_vals,
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            text=[f"${v:,.0f}" for v in y_vals],
            textposition="outside",
        )
    )
    fig.update_layout(
        title=f"Waterfall: Contribution to Inventory Value by {group_col}",
        yaxis_title="Inventory Value",
        showlegend=False,
    )
    return fig


def heatmap_chart(df, index_col, column_col):
    pivot = pd.pivot_table(
        df,
        values="Total_Inventory_Value",
        index=index_col,
        columns=column_col,
        aggfunc="sum",
        fill_value=0,
    )
    fig = px.imshow(
        pivot,
        text_auto=".2s",
        aspect="auto",
        color_continuous_scale="Blues",
        title=f"Heatmap of Inventory Value: {index_col} x {column_col}",
    )
    fig.update_layout(xaxis_title=column_col, yaxis_title=index_col)
    return fig


def pareto_table(df, group_col):
    pareto = (
        df.groupby(group_col, as_index=False)["Total_Inventory_Value"]
        .sum()
        .sort_values("Total_Inventory_Value", ascending=False)
    )
    total = pareto["Total_Inventory_Value"].sum()
    pareto["Share_%"] = (pareto["Total_Inventory_Value"] / total * 100).round(2) if total else 0
    pareto["Cumulative_%"] = pareto["Share_%"].cumsum().round(2)
    return pareto


st.title("📦 Streamlit Inventory Dashboard")
st.caption("Interactive slice-and-dice dashboard for inventory analysis")

with st.sidebar:
    st.subheader("Data source")
    uploaded_file = st.file_uploader("Upload a CSV", type=["csv"])

try:
    df = load_data(uploaded_file)
except FileNotFoundError:
    st.error(
        "No CSV found. Add 'Dummy_data_for_dummy_app.csv' to the repo root or upload a CSV from the sidebar."
    )
    st.stop()
except Exception as e:
    st.error(f"Could not load data: {e}")
    st.stop()

filtered_df = apply_filters(df)

if filtered_df.empty:
    st.warning("No data matches the current filter selection. Please broaden your filters.")
    st.stop()

# Top controls for chart dimensions
st.subheader("Analysis Controls")
col_a, col_b, col_c, col_d = st.columns(4)
possible_dims = ["Location", "Category", "Storage_Type", "Supplier_Region", "Criticality"]
bar_dim = col_a.selectbox("Bar chart dimension", possible_dims, index=0)
stack_dim = col_b.selectbox("Stacked bar dimension", possible_dims, index=1)
stack_color = col_c.selectbox("Stacked bar color", possible_dims, index=4)
waterfall_dim = col_d.selectbox("Waterfall dimension", possible_dims, index=1)

heat_a, heat_b = st.columns(2)
heatmap_row = heat_a.selectbox("Heatmap rows", possible_dims, index=0)
heatmap_col_options = [d for d in possible_dims if d != heatmap_row]
heatmap_col = heat_b.selectbox("Heatmap columns", heatmap_col_options, index=0)

st.markdown("---")
display_kpis(filtered_df)

# Charts
row1_col1, row1_col2 = st.columns(2)
row1_col1.plotly_chart(bar_chart(filtered_df, bar_dim), use_container_width=True)
row1_col2.plotly_chart(stacked_chart(filtered_df, stack_dim, stack_color), use_container_width=True)

row2_col1, row2_col2 = st.columns(2)
row2_col1.plotly_chart(scatter_chart(filtered_df), use_container_width=True)
row2_col2.plotly_chart(waterfall_chart(filtered_df, waterfall_dim), use_container_width=True)

st.plotly_chart(heatmap_chart(filtered_df, heatmap_row, heatmap_col), use_container_width=True)

# Detail section
st.subheader("Pareto / Contribution Table")
st.dataframe(pareto_table(filtered_df, waterfall_dim), use_container_width=True, hide_index=True)

st.subheader("Filtered Inventory Data")
st.dataframe(
    filtered_df.sort_values("Total_Inventory_Value", ascending=False),
    use_container_width=True,
    hide_index=True,
)

csv_download = filtered_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download filtered data as CSV",
    data=csv_download,
    file_name="filtered_inventory_data.csv",
    mime="text/csv",
)

with st.expander("How to deploy on Streamlit Community Cloud"):
    st.markdown(
        """
1. Create a GitHub repository.
2. Add these files to the repo root:
   - `app.py`
   - `requirements.txt`
   - `Dummy_data_for_dummy_app.csv` (or upload your own data in the app)
3. Go to Streamlit Community Cloud and connect your GitHub repo.
4. Set the main file path to `app.py`.
5. Deploy.
        """
    )


