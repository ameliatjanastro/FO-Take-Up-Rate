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

    # Get the most recent discount price per product
    discount_prices_sorted = discount_prices.sort_values(by=["Date"], ascending=False)
    discount_prices_latest = discount_prices_sorted.drop_duplicates(subset=["Product ID"], keep="first")
    
    # Compute discounted price
    discount_prices_latest["discounted_price"] = discount_prices_latest["Price"] - discount_prices_latest["Flushout Discount (IDR)"]

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
    df = discount_grouped.merge(discount_prices_latest[["Product ID", "Price", "discounted_price", "Flushout Discount (IDR)", "L1 Category", "Hub ID Fulfilled"]], 
                                on="Product ID", how="left")
    df = df.merge(normal_grouped, on=["Product ID", "Hub ID Fulfilled"], how="left")
    
    # Calculate Daily Sales Rates
    df["discounted_sales_rate"] = df["qty_sold_x"] / df["discount_days"]
    df["non_discounted_sales_rate"] = df["qty_sold_y"] / df["non_discount_days"]
    
    # Calculate Take-up Rate
    df["take_up_rate"] = df["discounted_sales_rate"] / df["non_discounted_sales_rate"]
    df["discount_percentage"] = (df["Flushout Discount (IDR)"] / df["Price"]).clip(upper=1) * 100

    df["discount_percentage_display"] = df["discount_percentage"].round(2).astype(str) + "%"
    df["take_up_rate_display"] = (df["take_up_rate"]*100).round(2).astype(str) + "%"
    
    best_discounts = df.loc[df.groupby(["Product ID", "Hub ID"])["take_up_rate"].idxmax(), 
                            ["Product ID", "Hub ID Fulfilled", "discount_percentage", "take_up_rate", "L1 Category", "Hub ID Fulfilled"]]
    
    # Merge best discount info
    df = df.merge(best_discounts, on=["Product ID", "Hub ID Fulfilled"], how="left", suffixes=("", "_best"))

    ### Sidebar Filters ###
    st.sidebar.subheader("Filters")
    
    # Dropdowns for L1 Category and Hub ID
    category_filter = st.sidebar.selectbox("Select L1 Category", ["All"] + sorted(df["L1 Category"].dropna().unique().tolist()))
    hub_filter = st.sidebar.selectbox("Select Hub ID", ["All"] + sorted(df["Hub ID Fulfilled"].dropna().astype(str).unique().tolist()))
    
    # Apply filters
    if category_filter != "All":
        df = df[df["L1 Category"] == category_filter]
    if hub_filter != "All":
        df = df[df["Hub ID Fulfilled"].astype(str) == hub_filter]
    
    ### Display Results ###
    st.subheader("Results")
    st.dataframe(df[["Product ID", "Hub ID", "take_up_rate_display", "discount_percentage_display"]])
    
    ### Graph: Discount Percentage vs Take-up Rate ###
    st.subheader("Best Discount % vs. Take-up Rate")
    fig = px.scatter(
        df, x="discount_percentage", y="take_up_rate", color="l1_category",
        hover_data=["Product ID", "Hub ID Fulfilled"], title="Effectiveness of Discounts"
    )
    st.plotly_chart(fig)
    
    ### Export CSV (keeping decimal format) ###
    export_df = df[["Product ID", "Hub ID Fulfilled", "take_up_rate", "discount_percentage"]]
    st.download_button("Download Results as CSV", export_df.to_csv(index=False), "take_up_rate_results.csv", "text/csv")

else:
    st.write("Upload all three CSV files to proceed.")
