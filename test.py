import streamlit as st
import pandas as pd
import plotly.express as px

# Streamlit App Title
st.title("SC Flushout vs Take-up Rate")

# Sidebar: Upload CSV files
st.sidebar.header("Upload Data")
discount_sales_file = st.sidebar.file_uploader("Upload FO Sales Data", type=["csv"])
normal_sales_file = st.sidebar.file_uploader("Upload Normal Sales Data", type=["csv"])
discount_price_file = st.sidebar.file_uploader("Upload FO Price Reduction", type=["csv"])

if discount_sales_file and discount_price_file and normal_sales_file:
    # Load only required columns
    discount_sales = pd.read_csv(discount_sales_file, usecols=["Date", "Product ID", "Hub ID Fulfilled","Location Name Fulfilled", "Product Name","Qty sold Discounted Price"], parse_dates=["Date"])
    normal_sales = pd.read_csv(normal_sales_file, usecols=["Date", "Product ID", "Hub ID Fulfilled","Location Name Fulfilled", "Product Name", "Total Qty Sold"], parse_dates=["Date"])
    discount_prices = pd.read_csv(discount_price_file, usecols=["Date","Product ID", "Product Name", "Price","Total Sales (Qty)", "Flushout Discount (IDR)", "L1 Category"], parse_dates=["Date"])

    # Merge sales data with discount price data
    df = discount_sales.merge(discount_prices, on=["Date","Product ID","Product Name"], how="left")
    df = df.merge(normal_sales, on=["Date", "Product ID", "Product Name", "Hub ID Fulfilled","Location Name Fulfilled"], how="left")

    # Fill missing values
    df.fillna(0, inplace=True)

    
    # Ensure Price column has valid values
    df["Price"] = df["Price"].replace(0, float("nan"))  # Prevent division by zero

    # Calculate discount percentage
    df["discount_percentage"] = (df["Flushout Discount (IDR)"]/df["Total Sales (Qty)"]) / df["Price"]

    # Aggregate sales data per product & hub (for independent best discount calculation)
    agg_df = df.groupby(["Product ID", "Product Name", "Hub ID Fulfilled"]).agg(
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
    df = df.merge(agg_df[["Product ID", "Product Name", "Hub ID Fulfilled", "avg_discount_percentage", "take_up_rate"]], on=["Product ID", "Product Name", "Hub ID Fulfilled"], how="left")
    df_best = df.groupby(["Product ID", "Product Name", "Hub ID Fulfilled"]).agg({
        "take_up_rate": "max"  # Best take-up rate found
    }).reset_index()
    df = df.merge(df_best, on=["Product ID", "Product Name", "Hub ID Fulfilled"], how="left", suffixes=("", "_best"))

    
    
    ### Sidebar Filters ###
    st.sidebar.subheader("Filters")

    # Multi-select for L1 Category
    #category_options = ["All"] + sorted(df.loc[df["L1 Category"] != 0, "L1 Category"].dropna().unique().tolist())
    #category_filter = st.sidebar.multiselect("Select L1 Category", category_options, default=category_options)

    # select for Hub ID
    # Combine Hub ID and Location Name for selection display
    df["Hub Selection"] = df["Hub ID Fulfilled"].astype(str) + " - " + df["Location Name Fulfilled"].astype(str)

    # Generate unique options
    hub_options = sorted(df["Hub Selection"].dropna().unique().tolist())

    # Sidebar selection with combined values
    hub_filter = st.sidebar.selectbox("Select Hub ID & Location", hub_options)

    # Apply filter
    selected_hub_id = hub_filter.split(" - ")[0]  # Extract Hub ID
    df = df[df["Hub ID Fulfilled"].astype(str) == selected_hub_id]

    ### Display Results ###
    st.markdown("----")    
    st.subheader("Best Discount % with highest Take-up Rate L14")
    df.columns = df.columns.str.strip()
    df["Product ID"] = df["Product ID"].astype(int)
    date_min = df["Date"].min().strftime("%Y-%m-%d")
    date_max = df["Date"].max().strftime("%Y-%m-%d")
    df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
    df["avg_discount_percentage"] = df["avg_discount_percentage"].replace([float("inf"), float("-inf")], 0).fillna(0)
    df["FO Discount %"] = (df["avg_discount_percentage"]*100).round(2).astype(str) + "%"
    df["take_up_rate_best"] = df["take_up_rate_best"].replace([float("inf"), float("-inf")], 0).fillna(0)
    df["Take Up Rate Performance"] = (df["take_up_rate_best"] * 100).round(2).astype(str) + "%"
    df = df.sort_values(by=["Product ID", "Product Name","take_up_rate_best"], ascending=[True, True, True])

    #st.dataframe(df[selected_columns], hide_index=True)
    # Get the minimum and maximum date from the dataset
    
    # Display the date range at the top
    st.markdown(f"<h6 style='text-align: left; color: red;'>Date Range: {date_min} to {date_max}</h6>", unsafe_allow_html=True)
    #df_view = df[selected_columns].drop_duplicates()

    df_view = df.drop_duplicates(subset=["Product ID"]).copy()
    
    # Convert "Take Up Rate Performance" to float (remove % sign first)
    df_view["Take Up Rate Performance"] = df_view["Take Up Rate Performance"].str.replace('%', '').astype(float) / 100
    
    selected_columns = ["Product ID", "Product Name", "FO Discount %", "Take Up Rate Performance"]
    def highlight_low_take_up_rate(row):
    if row["Take Up Rate Performance"] < 0.4:
        return ["background-color: #FBCEB1"] * len(row)  # Light Red for full row
    return [""] * len(row)

    # Apply styling to the dataframe
    styled_df = df_view.style.apply(highlight_low_take_up_rate, axis=1).format({
        "Take Up Rate Performance": "{:.2%}".format
    })
    
    # Display styled dataframe in Streamlit
    st.data_editor(
        df_view[selected_columns], 
        hide_index=True, 
        use_container_width=True,
        column_config={
            "Product ID": st.column_config.TextColumn(width="80px"),
            "Product Name": st.column_config.TextColumn(width="300px"),
            "FO Discount %": st.column_config.TextColumn(width="80px"),
            "Take Up Rate Performance": st.column_config.TextColumn(width="80px"),
        }
    )

    st.markdown(
    """
    <style>
    .stDataFrame { font-size: 9px !important; }
    </style>
    """,
    unsafe_allow_html=True
    )

    st.dataframe(styled_df, hide_index=True, use_container_width=True)
        
    ### Graph: Average Discount Percentage vs Take-up Rate ###
    #st.subheader("Best Discount % vs. Take-up Rate (Avg. L1 Category)")
    
    df_avg = df.groupby("L1 Category", as_index=False).agg({
        "discount_percentage": "mean",
        "take_up_rate_best": "mean"
    })

    df_avg["discount_label"] = (df_avg["discount_percentage"]*100).round(2).astype(str) + "%"

    df_avg = df_avg.sort_values(by="take_up_rate_best", ascending=True)

    fig = px.bar(
        df_avg, 
        x="take_up_rate_best", 
        y="L1 Category", 
        orientation="h",  # Horizontal bar chart
        title="Effectiveness of Discounts (Averaged by L1 Category)",
        text="discount_label",  # Show discount percentage as text
    )
    
    # Adjust text position to be on the left of the bars
    fig.update_traces(textposition="outside")  

    # Extend x-axis to zoom out the chart (adds padding)
    max_take_up_rate = df_avg["take_up_rate_best"].max()
    fig.update_layout(
        xaxis_title="Take-up Rate (%)",
        yaxis_title="L1 Category",
        xaxis=dict(range=[0, max_take_up_rate * 1.2]),  # 20% extra space on the right
    )
    
    # Show the chart in Streamlit
    st.plotly_chart(fig)
    
    
    ### Export CSV ###
    export_df = df[["Date", "Product ID", "Hub ID Fulfilled", "avg_discount_percentage", "take_up_rate_best"]]
    st.download_button("Download Results as CSV", export_df.to_csv(index=False), "take_up_rate_results.csv", "text/csv")

else:
    st.write("Upload all three CSV files to proceed.")
