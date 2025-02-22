import streamlit as st
import pandas as pd
import plotly.express as px

# Streamlit App Title
st.title("Campaign Take-up Rate Calculator")

# Sidebar: Upload CSV files
st.sidebar.header("Upload Data")
discount_sales_file = st.sidebar.file_uploader("Upload Discount Sales CSV", type=["csv"])
discount_price_file = st.sidebar.file_uploader("Upload Discount Price CSV", type=["csv"])
normal_sales_file = st.sidebar.file_uploader("Upload Normal Sales CSV", type=["csv"])

if discount_sales_file and discount_price_file and normal_sales_file:
    # Load Data
    discount_sales = pd.read_csv(discount_sales_file, parse_dates=["Date"])
    discount_prices = pd.read_csv(discount_price_file, parse_dates=["Date"])
    normal_sales = pd.read_csv(normal_sales_file, parse_dates=["Date"])

    # Standardize column names
    discount_prices = discount_prices.rename(columns=lambda x: x.strip())

    # Ensure required columns exist
    expected_columns = ["Date", "Product ID", "Price", "Flushout Discount (IDR)", "L1 Category"]
    missing_cols = [col for col in expected_columns if col not in discount_prices.columns]
    if missing_cols:
        st.error(f"Missing columns in discount price file: {missing_cols}")
        st.stop()

    # Fill NaN values to avoid calculation errors
    discount_sales["Qty sold Discounted Price"] = discount_sales["Qty sold Discounted Price"].fillna(0)
    normal_sales["Total Qty Sold"] = normal_sales["Total Qty Sold"].fillna(0)
    discount_prices["Flushout Discount (IDR)"] = discount_prices["Flushout Discount (IDR)"].fillna(0)

    # Merge discount sales with discount prices (keeping Date)
    df = discount_sales.merge(
        discount_prices[["Date", "Product ID", "Price", "Flushout Discount (IDR)", "L1 Category"]],
        on=["Date", "Product ID"],
        how="left"
    ).merge(
        normal_sales, on=["Date","Hub ID Order","Hub Name Order","Hub ID Fulfilled","Location Name Fulfilled","Product ID","Product Name","SKU Number","L1 Category","Total Qty Sold","Total Goods Value (IDR)","Qty sold Discounted Price","Total Price Cut (IDR)"], how="left"
    )

    # Compute discount percentage
    df["Price"] = df["Price"].replace(0, float("nan"))  # Avoid division by zero
    df["discount_percentage"] = df["Flushout Discount (IDR)"] / df["Price"]
    st.write(df.head())
    # Compute daily sales rates
    df["discounted_sales_rate"] = df["Qty sold Discounted Price"]
    df["non_discounted_sales_rate"] = df["Total Qty Sold"]

    # Compute take-up rate (per date)
    df["take_up_rate"] = df["discounted_sales_rate"] / df["non_discounted_sales_rate"]

    ### **Find Best Discount Percentage (Ignoring Date)**
    df_best = df.groupby(["Product ID", "Hub ID Fulfilled"]).agg({
        "discount_percentage": "max",  # Best discount found
        "take_up_rate": "max"  # Best take-up rate found
    }).reset_index()

    # Merge best discount & take-up rate back into the dataset
    df = df.merge(df_best, on=["Product ID", "Hub ID Fulfilled"], how="left", suffixes=("", "_best"))

    ### **Sidebar Filters**
    st.sidebar.subheader("Filters")

    # L1 Category Multi-Select
    if "L1 Category" in df.columns:
        df["L1 Category"] = df["L1 Category"].astype(str)
        category_options = sorted(df["L1 Category"].dropna().unique().tolist())
    else:
        category_options = []
    category_filter = st.sidebar.multiselect("Select L1 Category", category_options, default=category_options)

    # Hub ID Filter
    hub_options = sorted(df["Hub ID Fulfilled"].dropna().astype(str).unique().tolist())
    hub_filter = st.sidebar.selectbox("Select Hub ID", ["All"] + hub_options)

    # Apply filters
    if category_filter:
        df = df[df["L1 Category"].isin(category_filter)]
    if hub_filter != "All":
        df = df[df["Hub ID Fulfilled"].astype(str) == hub_filter]

    ### **Display Take-up Rate Table with Dates**
    st.subheader("Take-up Rate Per Date")
    st.dataframe(df[["Date", "Product ID", "Hub ID Fulfilled", "L1 Category", 
                     "take_up_rate", "discount_percentage", "discount_percentage_best", "take_up_rate_best"]])

    ### **Graph: Best Discount % vs. Take-up Rate (Ignoring Dates)**
    df_avg = df.groupby("L1 Category", as_index=False).agg({
        "discount_percentage_best": "mean",
        "take_up_rate_best": "mean"
    })

    fig = px.scatter(
        df_avg, 
        x="discount_percentage_best", 
        y="take_up_rate_best", 
        text="L1 Category",  
        title="Best Discount % vs. Take-up Rate (Averaged by L1 Category)"
    )
    fig.update_traces(textposition="top center")
    st.plotly_chart(fig)

    ### **Download CSV**
    export_df = df[["Product ID", "Hub ID Fulfilled", "take_up_rate", "discount_percentage"]]
    st.download_button("Download Results as CSV", export_df.to_csv(index=False), "take_up_rate_results.csv", "text/csv")

else:
    st.write("Upload all three CSV files to proceed.")



