import streamlit as st
import pandas as pd

# Upload CSV files
st.title("Campaign Take-up Rate Calculator")

st.sidebar.header("Upload Data")
discount_sales_file = st.sidebar.file_uploader("Upload Discount Sales CSV", type=["csv"])
discount_price_file = st.sidebar.file_uploader("Upload Discount Price CSV", type=["csv"])
normal_sales_file = st.sidebar.file_uploader("Upload Normal Sales CSV", type=["csv"])

if discount_sales_file and discount_price_file and normal_sales_file:
    # Load Data
    discount_sales = pd.read_csv(discount_sales_file, parse_dates=["Date"])
    discount_prices = pd.read_csv(discount_price_file)
    normal_sales = pd.read_csv(normal_sales_file, parse_dates=["Date"])
    
    # Aggregate sales data
    discount_grouped = discount_sales.groupby(["Product ID", "Hub ID Fulfilled"]).agg(
        qty_sold=("Qty sold Discounted Price", "sum"),
        discount_days=("Date", "nunique")
    ).reset_index()
    
    normal_grouped = normal_sales.groupby(["Product ID", "Hub ID Fulfilled"]).agg(
        qty_sold=("Total Qty Sold", "sum"),
        non_discount_days=("Date", "nunique")
    ).reset_index()
    
    # Merge Data
    df = discount_grouped.merge(discount_prices, on=["Product ID"], how="left")
    df = df.merge(normal_grouped, on=["Product ID", "Hub ID Fulfilled"], how="left")
    
    # Calculate Daily Sales Rates
    df["discounted_sales_rate"] = df["qty_sold_x"] / df["discount_days"]
    df["non_discounted_sales_rate"] = df["qty_sold_y"] / df["non_discount_days"]
    
    # Calculate Take-up Rate
    df["take_up_rate"] = df["discounted_sales_rate"] / df["non_discounted_sales_rate"]
    df["discount_percentage"] = (df["Flushout Discount (IDR)"] / df["Price"]) * 100

    df["discount_percentage_display"] = df["discount_percentage"].round(2).astype(str) + "%"
    df["take_up_rate_display"] = df["take_up_rate"].round(2).astype(str) + "%"
    # Display Results
    st.subheader("Results")
    st.dataframe(df[["Product ID", "Hub ID Fulfilled", "take_up_rate_display", "discount_percentage_display"]])

    # Export CSV (keep decimal format)
    export_df = df[["product_id", "location_id", "take_up_rate", "discount_percentage"]]
    st.download_button("Download Results as CSV", export_df.to_csv(index=False), "take_up_rate_results.csv", "text/csv")

else:
    st.write("Upload all three CSV files to proceed.")
