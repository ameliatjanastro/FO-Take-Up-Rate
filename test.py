import streamlit as st
import pandas as pd
import plotly.express as px

# Streamlit App Title
st.title("Campaign Take-up Rate Calculator")

# Sidebar: Upload CSV files
st.sidebar.header("Upload Data")
# Load only required columns
discount_sales = pd.read_csv(discount_sales_file, usecols=["Date", "Product ID", "Hub ID Fulfilled", "Qty sold Discounted Price"], parse_dates=["Date"])
normal_sales = pd.read_csv(normal_sales_file, usecols=["Date", "Product ID", "Hub ID Fulfilled", "Total Qty Sold"], parse_dates=["Date"])
discount_prices = pd.read_csv(discount_price_file, usecols=["Product ID", "Price", "Flushout Discount (IDR)", "L1 Category"], parse_dates=["Date"])

# Merge the datasets
df = discount_sales.merge(discount_prices, on="Product ID", how="left")
df = df.merge(normal_sales, on=["Date", "Product ID", "Hub ID Fulfilled"], how="left")

# Fill missing values
df.fillna(0, inplace=True)

# Compute discount percentage
df["Flushout Discount (IDR)"] = df["Flushout Discount (IDR)"].fillna(0)
df["Price"] = df["Price"].replace(0, float("nan"))  # Prevent division by zero
df["discount_percentage"] = df["Flushout Discount (IDR)"] / df["Price"]

# Compute sales rates
df["discounted_sales_rate"] = df["Qty sold Discounted Price"] / df.groupby(["Product ID", "Hub ID Fulfilled"])["Date"].transform("nunique")
df["non_discounted_sales_rate"] = df["Total Qty Sold"] / df.groupby(["Product ID", "Hub ID Fulfilled"])["Date"].transform("nunique")

# Take-up rate calculation
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



