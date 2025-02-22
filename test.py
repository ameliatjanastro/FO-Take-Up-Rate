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
    # Load only required columns
    discount_sales = pd.read_csv(discount_sales_file, usecols=["Date", "Product ID", "Hub ID Fulfilled", "Qty sold Discounted Price"], parse_dates=["Date"])
    normal_sales = pd.read_csv(normal_sales_file, usecols=["Date", "Product ID", "Hub ID Fulfilled", "Total Qty Sold"], parse_dates=["Date"])
    discount_prices = pd.read_csv(discount_price_file, usecols=["Date","Product ID", "Price","Total Sales (Qty)", "Flushout Discount (IDR)", "L1 Category"], parse_dates=["Date"])

    # Merge sales data with discount price data
    df = discount_sales.merge(discount_prices, on=["Date","Product ID"], how="left")
    df = df.merge(normal_sales, on=["Date", "Product ID", "Hub ID Fulfilled"], how="left")

    # Fill missing values
    df.fillna(0, inplace=True)
    df["Product ID"] = df["Product ID"].astype(str).str.replace(",", "")
    df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
    
    # Ensure Price column has valid values
    df["Price"] = df["Price"].replace(0, float("nan"))  # Prevent division by zero

    # Calculate discount percentage
    df["discount_percentage"] = (df["Flushout Discount (IDR)"]/df["Total Sales (Qty)"]) / df["Price"]

    # Aggregate sales data per product & hub (for independent best discount calculation)
    agg_df = df.groupby(["Product ID", "Hub ID Fulfilled"]).agg(
        total_discounted_sales=("Qty sold Discounted Price", "sum"),
        total_non_discounted_sales=("Total Qty Sold", "sum"),
        discount_days=("Date", "nunique"),
        non_discount_days=("Date", "nunique"),
        avg_discount_percentage=("discount_percentage", "mean")
    ).reset_index()

    # Compute sales rates
    agg_df["discounted_sales_rate"] = agg_df["total_discounted_sales"] / agg_df["discount_days"]
    agg_df["non_discounted_sales_rate"] = agg_df["total_non_discounted_sales"] / agg_df["non_discount_days"]

    # Take-up rate calculation
    agg_df["take_up_rate"] = agg_df["discounted_sales_rate"] / agg_df["non_discounted_sales_rate"]

    # Merge best discount info back into df for detailed date view
    df = df.merge(agg_df[["Product ID", "Hub ID Fulfilled", "avg_discount_percentage", "take_up_rate"]], on=["Product ID", "Hub ID Fulfilled"], how="left")
    df_best = df.groupby(["Product ID", "Hub ID Fulfilled"]).agg({
        "discount_percentage": "max",  # Best discount found
        "take_up_rate": "max"  # Best take-up rate found
    }).reset_index()
    df = df.merge(df_best, on=["Product ID", "Hub ID Fulfilled"], how="left", suffixes=("", "_best"))

    
    
    ### Sidebar Filters ###
    st.sidebar.subheader("Filters")

    # Multi-select for L1 Category
    #category_options = ["All"] + sorted(df.loc[df["L1 Category"] != 0, "L1 Category"].dropna().unique().tolist())
    #category_filter = st.sidebar.multiselect("Select L1 Category", category_options, default=category_options)

    # Multi-select for Hub ID
    hub_options = sorted(df["Hub ID Fulfilled"].dropna().astype(str).unique().tolist())
    hub_filter = st.sidebar.selectbox("Select Hub ID", ["All"] + hub_options)

    # Apply filters
    #df = df[df["L1 Category"].isin(category_filter)]
    if hub_filter != "All":
        df = df[df["Hub ID Fulfilled"].astype(str) == hub_filter]

    ### Display Results ###
    
    st.subheader("Take-up Rate Data (With Dates)")
    df.columns = df.columns.str.strip()
    df["FO Discount %"] = (df["discount_percentage_best"]*100).round(2).astype(str) + "%"
    df["Take Up Rate Ideal"] = (df["take_up_rate_best"] * 100).round(2).astype(str) + "%"
    selected_columns = [col for col in ["Date", "Product ID", "Hub ID Fulfilled", "discount_percentage_best", "take_up_rate_best", "FO Discount %", "Take Up Rate Ideal"] if col in df.columns]

    st.dataframe(df[selected_columns], hide_index=True)

    ### Graph: Average Discount Percentage vs Take-up Rate ###
    st.subheader("Best Discount % vs. Take-up Rate (Averaged)")

    df_avg = df.groupby("L1 Category", as_index=False).agg({
        "discount_percentage_best": "mean",
        "take_up_rate_best": "mean"
    })

    fig = px.scatter(
        df_avg, 
        x="discount_percentage_best", 
        y="take_up_rate_best", 
        text="L1 Category",  
        title="Effectiveness of Discounts (Averaged by L1 Category)"
    )

    fig.update_traces(textposition="top center")
    st.plotly_chart(fig)

    ### Export CSV ###
    export_df = df[["Product ID", "Hub ID Fulfilled", "take_up_rate_best", "discount_percentage_best"]]
    st.download_button("Download Results as CSV", export_df.to_csv(index=False), "take_up_rate_results.csv", "text/csv")

else:
    st.write("Upload all three CSV files to proceed.")
