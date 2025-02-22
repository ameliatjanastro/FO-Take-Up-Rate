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

    # Standardize column names (strip spaces)
    discount_prices = discount_prices.rename(columns=lambda x: x.strip())

    # Ensure column names are correct
    expected_columns = ["Date", "Product ID", "Price", "Flushout Discount (IDR)", "L1 Category"]
    missing_cols = [col for col in expected_columns if col not in discount_prices.columns]
    
    if missing_cols:
        st.error(f"Missing columns in discount price file: {missing_cols}")
        st.stop()

    # Sort discount prices by date (most recent first)
    #discount_prices_sorted = discount_prices.sort_values(by=["Date"], ascending=False)

    
    

    # Aggregate discount sales
    discount_grouped = discount_sales.groupby(["Product ID", "Hub ID Fulfilled", "Date"]).agg(
        qty_sold=("Qty sold Discounted Price", "sum")
    ).reset_index()

    # Aggregate normal sales (calculate average daily sales)
    normal_grouped = normal_sales.groupby(["Product ID", "Hub ID Fulfilled"]).agg(
        avg_qty_sold=("Total Qty Sold", "mean"),  # Average per active day
        total_qty_sold=("Total Qty Sold", "sum"),
        non_discount_days=("Date", "nunique")
    ).reset_index()

    # Merge discount and normal sales data
    df1 = discount_grouped.merge(normal_grouped, on=["Product ID", "Hub ID Fulfilled","L1 Category"], how="left")
    df = df1.merge(
    discount_prices[["Date", "Product ID", "Price", "Flushout Discount (IDR)", "L1 Category"]],
    on=["Date", "Product ID","L1 Category"],
    how="left"
)
    
    # Ensure no missing columns before calculations
    if "Flushout Discount (IDR)" in df.columns and "Price" in df.columns:
        df["Flushout Discount (IDR)"] = df["Flushout Discount (IDR)"].fillna(0)
        df["Price"] = df["Price"].replace(0, float("nan"))  # Prevent division by zero
        df["discount_percentage"] = (df["Flushout Discount (IDR)"] / df["Price"]) * 100
    else:
        st.error("Missing 'Flushout Discount (IDR)' or 'Price' column after merging. Check input files.")
        st.stop()

    
    # Compute discounted price
    #df["discounted_price"] = df["Price"] - df["Flushout Discount (IDR)"]

    # Fill NaN values with 0
    df.fillna(0, inplace=True)

    # Calculate Take-up Rate (Comparing daily sales rates)
    df["take_up_rate"] = df["qty_sold"] / df["avg_qty_sold"]
    
    # Calculate Discount Percentage
    #df["discount_percentage"] = (df["Flushout Discount (IDR)"] / df["Price"])* 100

    # Round for Display
    df["discount_percentage_display"] = df["discount_percentage"].round(2).astype(str) + "%"
    df["take_up_rate_display"] = (df["take_up_rate"] * 100).round(2).astype(str) + "%"

    # Find the best discount percentage (highest take-up rate per product & hub)
    best_discounts = df.loc[df.groupby(["Product ID", "Hub ID Fulfilled"])["take_up_rate"].idxmax(), 
                            ["Product ID", "Hub ID Fulfilled", "discount_percentage", "take_up_rate", "L1 Category"]]

    # Merge best discount info back into df
    df = df.merge(best_discounts, on=["Product ID", "Hub ID Fulfilled"], how="left", suffixes=("", "_best"))

    ### Sidebar Filters ###
    st.sidebar.subheader("Filters")
    
    # Dropdowns for L1 Category and Hub ID
    if "L1 Category" in df.columns:
        df["L1 Category"] = df["L1 Category"].astype(str)  # Ensure all values are strings
        category_options = ["All"] + sorted(df["L1 Category"].dropna().unique().tolist())
    else:
        category_options = ["All"]
    category_filter = st.sidebar.selectbox("Select L1 Category", category_options)
    hub_filter = st.sidebar.selectbox("Select Hub ID", ["All"] + sorted(df["Hub ID Fulfilled"].dropna().astype(str).unique().tolist()))
    
    # Apply filters
    if category_filter != "All":
        df = df[df["L1 Category"] == category_filter]
    if hub_filter != "All":
        df = df[df["Hub ID Fulfilled"].astype(str) == hub_filter]

    ### Display Results ###
    st.subheader("Results")
    st.dataframe(df[["Product ID", "Hub ID Fulfilled", "take_up_rate_display", "discount_percentage_display"]])
    
    ### Graph: Discount Percentage vs Take-up Rate ###
    st.subheader("Best Discount % vs. Take-up Rate")
    fig = px.scatter(
        df, x="discount_percentage", y="take_up_rate", color="L1 Category",
        hover_data=["Product ID", "Hub ID Fulfilled"], title="Effectiveness of Discounts"
    )
    st.plotly_chart(fig)
    
    ### Export CSV (keeping decimal format) ###
    export_df = df[["Product ID", "Hub ID Fulfilled", "take_up_rate", "discount_percentage"]]
    st.download_button("Download Results as CSV", export_df.to_csv(index=False), "take_up_rate_results.csv", "text/csv")

else:
    st.write("Upload all three CSV files to proceed.")


