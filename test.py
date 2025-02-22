import streamlit as st
import pandas as pd
import plotly.express as px

# Upload CSV files
st.title("Campaign Take-up Rate Calculator")

st.sidebar.header("Upload Data")
discount_sales_file = st.sidebar.file_uploader("Upload Discount Sales CSV", type=["csv"])
discount_price_file = st.sidebar.file_uploader("Upload Discount Price CSV", type=["csv"])
normal_sales_file = st.sidebar.file_uploader("Upload Normal Sales CSV", type=["csv"])

if discount_sales_file and discount_price_file and normal_sales_file:
    # Load Data
    discount_sales = pd.read_csv(discount_sales_file, parse_dates=["Date"])
    discount_prices = pd.read_csv(discount_price_file, parse_dates=["Date"])
    normal_sales = pd.read_csv(normal_sales_file, parse_dates=["Date"])

    # Ensure column names are correct
    discount_prices = discount_prices.rename(columns={"Product ID": "product_id", "Price": "normal_price", 
                                                      "Flushout Discount (IDR)": "discount_amount", 
                                                      "L1 Category": "l1_category", "Hub ID Fulfilled": "hub_id"})
    
    # Get the most recent discount price per product
    #discount_prices_sorted = discount_prices.sort_values(by=["Date"], ascending=False)
    #discount_prices_latest = discount_prices.drop_duplicates(subset=["product_id", "hub_id"], keep="first")
    
    # Compute discounted price
    discount_prices["discounted_price"] = discount_prices["normal_price"] - discount_prices["discount_amount"]

    # Aggregate sales data
    discount_grouped = discount_sales.groupby(["product_id", "hub_id"]).agg(
        qty_sold=("Qty sold Discounted Price", "sum"),
        discount_days=("Date", "nunique")
    ).reset_index()
    
    normal_grouped = normal_sales.groupby(["product_id", "hub_id"]).agg(
        qty_sold=("Total Qty Sold", "sum"),
        non_discount_days=("Date", "nunique")
    ).reset_index()
    
    # Merge Data
    df = discount_grouped.merge(discount_prices[["product_id", "normal_price", "discounted_price", "discount_amount", "l1_category", "hub_id"]], 
                                on=["product_id", "hub_id"], how="left")
    df = df.merge(normal_grouped, on=["product_id", "hub_id"], how="left")

    # Fill NaN values to prevent calculation errors
    df.fillna(0, inplace=True)
    
    # Calculate Discount Percentage
    df["discount_percentage"] = (df["discount_amount"] / df["normal_price"]).clip(upper=1) * 100

    # Calculate Daily Sales Rates
    df["discounted_sales_rate"] = df["qty_sold_x"] / df["discount_days"]
    df["non_discounted_sales_rate"] = df["qty_sold_y"] / df["non_discount_days"]
    
    # Calculate Take-up Rate
    df["take_up_rate"] = df["discounted_sales_rate"] / df["non_discounted_sales_rate"]

    # Round for display
    df["discount_percentage_display"] = df["discount_percentage"].round(2).astype(str) + "%"
    df["take_up_rate_display"] = (df["take_up_rate"] * 100).round(2).astype(str) + "%"

    # Find the best discount percentage (highest take-up rate)
    best_discounts = df.loc[df.groupby(["product_id", "hub_id"])["take_up_rate"].idxmax(), 
                            ["product_id", "hub_id", "discount_percentage", "take_up_rate", "l1_category"]]
    
    # Merge best discount info
    df = df.merge(best_discounts, on=["product_id", "hub_id"], how="left", suffixes=("", "_best"))

    ### Sidebar Filters ###
    st.sidebar.subheader("Filters")
    
    # Dropdowns for L1 Category and Hub ID
    category_filter = st.sidebar.selectbox("Select L1 Category", ["All"] + sorted(df["l1_category"].dropna().unique().tolist()))
    hub_filter = st.sidebar.selectbox("Select Hub ID", ["All"] + sorted(df["hub_id"].dropna().astype(str).unique().tolist()))
    
    # Apply filters
    if category_filter != "All":
        df = df[df["l1_category"] == category_filter]
    if hub_filter != "All":
        df = df[df["hub_id"].astype(str) == hub_filter]
    
    ### Display Results ###
    st.subheader("Results")
    st.dataframe(df[["Date", "product_id", "hub_id", "take_up_rate_display", "discount_percentage_display"]])
    
    ### Graph: Discount Percentage vs Take-up Rate ###
    st.subheader("Best Discount % vs. Take-up Rate")
    fig = px.scatter(
        df, x="discount_percentage", y="take_up_rate", color="l1_category",
        hover_data=["product_id", "hub_id"], title="Effectiveness of Discounts"
    )
    st.plotly_chart(fig)
    
    ### Export CSV (keeping decimal format) ###
    export_df = df[["Date", "product_id", "hub_id", "take_up_rate", "discount_percentage"]]
    st.download_button("Download Results as CSV", export_df.to_csv(index=False), "take_up_rate_results.csv", "text/csv")

else:
    st.write("Upload all three CSV files to proceed.")
