import streamlit as st
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
import io

# Page configuration
st.set_page_config(
    page_title="Response Visualizer",
    page_icon="📊",
    layout="wide"
)

# URL for the Google Sheet CSV export
SHEET_URL = "https://docs.google.com/spreadsheets/d/1PIhDB-RqQguZl6kGb19_ZkXcVvMYJwMmflgaiZ0PDDQ/export?format=csv"

@st.cache_data(ttl=60)
def load_data():
    try:
        df = pd.read_csv(SHEET_URL)
        # Clean column names
        df.columns = df.columns.str.strip()
        
        # Convert Timestamp to datetime
        if 'Timestamp' in df.columns:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')

        # Convert Expected Closure Date to datetime
        if 'Expected Closure Date' in df.columns:
            df['Expected Closure Date'] = pd.to_datetime(df['Expected Closure Date'], errors='coerce')
            
        # Convert CLOSED AMOUNT to numeric
        if 'CLOSED AMOUNT' in df.columns:
            df['CLOSED AMOUNT'] = pd.to_numeric(df['CLOSED AMOUNT'], errors='coerce').fillna(0)
            
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

def generate_eod_image(date_str, df):
    # Prepare data for table
    table_data = []
    headers = ['BDE Name', 'Company', 'Plan', 'Exp. Closure']
    
    # Sort by BDE
    if 'BDE NAME' in df.columns:
        df_sorted = df.sort_values('BDE NAME')
    else:
        df_sorted = df
        
    for _, row in df_sorted.iterrows():
        bde = str(row.get('BDE NAME', 'N/A'))
        # Truncate company name if too long
        company = str(row.get('COMPANY NAME', 'N/A'))
        if len(company) > 20:
            company = company[:17] + "..."
            
        plan = str(row.get('PLAN', 'N/A'))
        
        exp_closure = row.get('Expected Closure Date', pd.NaT)
        if pd.notna(exp_closure):
            # Format as DD-Mon (e.g., 30-Nov)
            exp_closure_str = exp_closure.strftime('%d-%b')
        else:
            exp_closure_str = "-"
            
        table_data.append([bde, company, plan, exp_closure_str])
        
    # Add Total Row
    table_data.append(['TOTAL', f"{len(df)} Responses", "", ""])

    # Calculate figure height
    # Header + Rows
    num_rows = len(table_data) + 1 
    # Base height 1.0 + 0.5 per row
    fig_height = 1.0 + (num_rows * 0.5)
    
    fig, ax = plt.subplots(figsize=(12, fig_height))
    ax.axis('off')
    
    # Title
    ax.set_title(f"EOD Report - {date_str}", fontsize=16, weight='bold', pad=20)
    
    # Table
    the_table = ax.table(cellText=table_data,
                         colLabels=headers,
                         loc='center',
                         cellLoc='left',
                         colWidths=[0.2, 0.35, 0.25, 0.2])
    
    the_table.auto_set_font_size(False)
    the_table.set_fontsize(12)
    the_table.scale(1, 2) # Increase row height
    
    # Styling
    for (row, col), cell in the_table.get_celld().items():
        if row == 0: # Header
            cell.set_text_props(weight='bold', color='white')
            cell.set_facecolor('#40466e')
        elif row == len(table_data): # Total row
            cell.set_text_props(weight='bold')
            cell.set_facecolor('#f0f2f6')
            
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return buf

def main():
    st.title("📊 Response Visualizer")

    df = load_data()
    
    if df.empty:
        st.warning("No data available or failed to load data.")
        return

    # Sidebar Filters
    st.sidebar.header("Filters")
    
    # BDE Filter
    bde_options = ['All BDEs'] + sorted(df['BDE NAME'].dropna().unique().tolist()) if 'BDE NAME' in df.columns else ['All BDEs']
    selected_bde = st.sidebar.selectbox("Filter by BDE", bde_options)
    
    # Plan Filter
    plan_options = ['All Plans'] + sorted(df['PLAN'].dropna().unique().tolist()) if 'PLAN' in df.columns else ['All Plans']
    selected_plan = st.sidebar.selectbox("Filter by Plan", plan_options)
    
    # Date Range Filter
    st.sidebar.markdown("---")
    enable_date_filter = st.sidebar.checkbox("Filter Dashboard by Date", value=False)
    start_date, end_date = None, None
    
    if enable_date_filter:
        date_range = st.sidebar.date_input(
            "Select Date Range",
            value=(pd.Timestamp.now().date(), pd.Timestamp.now().date()),
            key="dashboard_date_range"
        )
        if isinstance(date_range, tuple):
            if len(date_range) == 2:
                start_date, end_date = date_range
            elif len(date_range) == 1:
                start_date = date_range[0]
                end_date = start_date

    if st.sidebar.button("Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    # Apply BDE & Plan Filters (Base Data)
    base_df = df.copy()
    if selected_bde != 'All BDEs':
        base_df = base_df[base_df['BDE NAME'] == selected_bde]
    
    if selected_plan != 'All Plans':
        base_df = base_df[base_df['PLAN'] == selected_plan]

    # Apply Date Filter for Dashboard Views
    filtered_df = base_df.copy()
    if enable_date_filter and start_date and end_date and 'Timestamp' in filtered_df.columns:
        # Filter by Timestamp (Response Date)
        mask = (filtered_df['Timestamp'].dt.date >= start_date) & (filtered_df['Timestamp'].dt.date <= end_date)
        filtered_df = filtered_df[mask]

    # Metrics
    total_responses = len(filtered_df)
    total_closed_amount = filtered_df['CLOSED AMOUNT'].sum() if 'CLOSED AMOUNT' in filtered_df.columns else 0

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Responses", total_responses)
    with col2:
        st.metric("Total Closed Amount", f"₹{total_closed_amount:,.2f}")

    st.markdown("---")

    # Daily Activity & EOD Report Section
    st.subheader("📝 Daily Activity & EOD Report")
    
    if 'Timestamp' in base_df.columns:
        # Date Picker for EOD Report
        col_date, _ = st.columns([1, 3])
        with col_date:
            report_date = st.date_input("Select Date for Report", value=pd.Timestamp.now().date(), key="eod_date_picker")
        
        # Filter base_df (which has BDE/Plan filters but NO date range filter) by the specific report date
        report_date_ts = pd.Timestamp(report_date)
        daily_responses = base_df[base_df['Timestamp'].dt.date == report_date]
        
        col_today1, col_today2 = st.columns([2, 1])
        
        with col_today1:
            if not daily_responses.empty:
                st.success(f"Found {len(daily_responses)} responses for {report_date.strftime('%d-%b-%Y')}!")
                display_cols_today = [c for c in ['Timestamp', 'BDE NAME', 'COMPANY NAME', 'PLAN', 'CLOSED AMOUNT'] if c in daily_responses.columns]
                st.dataframe(daily_responses[display_cols_today], use_container_width=True)
            else:
                st.info(f"No responses found for {report_date.strftime('%d-%b-%Y')}.")

        with col_today2:
            st.write(f"### EOD Report ({report_date.strftime('%d-%b')})")
            if not daily_responses.empty:
                # Generate Image
                img_buf = generate_eod_image(report_date.strftime('%Y-%m-%d'), daily_responses)
                
                st.image(img_buf, caption=f"EOD Report - {report_date.strftime('%d-%b')}", use_container_width=True)
                
                st.download_button(
                    label="📥 Download EOD Report (PNG)",
                    data=img_buf,
                    file_name=f"EOD_Report_{report_date.strftime('%Y-%m-%d')}.png",
                    mime="image/png"
                )
            else:
                st.write("No data to generate report.")

    st.markdown("---")

    # Closure Insights Section
    st.subheader("📅 Closure Insights")
    
    if 'Expected Closure Date' in filtered_df.columns:
        today = pd.Timestamp.now().normalize()
        
        # Today's Closures
        todays_closures = filtered_df[filtered_df['Expected Closure Date'].dt.normalize() == today]
        
        # Upcoming Closures (Next 7 days)
        upcoming_closures = filtered_df[
            (filtered_df['Expected Closure Date'].dt.normalize() > today) & 
            (filtered_df['Expected Closure Date'].dt.normalize() <= today + pd.Timedelta(days=7))
        ]
        
        tab1, tab2 = st.tabs(["Today's Closures", "Upcoming Closures (Next 7 Days)"])
        
        cols_to_show = [c for c in ['BDE NAME', 'COMPANY NAME', 'Expected Closure Date', 'PLAN', 'CLOSED AMOUNT', 'MOBILE NO'] if c in filtered_df.columns]

        with tab1:
            if not todays_closures.empty:
                st.success(f"Found {len(todays_closures)} closures expected today!")
                st.dataframe(
                    todays_closures[cols_to_show],
                    use_container_width=True
                )
            else:
                st.info("No closures expected for today.")
                
        with tab2:
            if not upcoming_closures.empty:
                st.dataframe(
                    upcoming_closures[cols_to_show].sort_values('Expected Closure Date'),
                    use_container_width=True
                )
            else:
                st.info("No upcoming closures in the next 7 days.")
    else:
        st.warning("Column 'Expected Closure Date' not found in data.")

    st.markdown("---")

    # Charts
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        if 'BDE NAME' in filtered_df.columns and not filtered_df.empty:
            bde_metrics = filtered_df.groupby('BDE NAME').agg({
                'BDE NAME': 'count',
                'CLOSED AMOUNT': 'sum'
            }).rename(columns={'BDE NAME': 'Count'}).reset_index()
            
            fig_bde = px.bar(
                bde_metrics, 
                x='BDE NAME', 
                y='Count', 
                title='Responses by BDE',
                color='CLOSED AMOUNT',
                hover_data=['CLOSED AMOUNT'],
                labels={'Count': 'Number of Responses', 'CLOSED AMOUNT': 'Revenue'}
            )
            st.plotly_chart(fig_bde, use_container_width=True)
            
            # Detailed BDE View
            with st.expander("View Detailed BDE & Company List"):
                display_cols = [c for c in ['BDE NAME', 'COMPANY NAME', 'Expected Closure Date', 'PLAN', 'CLOSED AMOUNT'] if c in filtered_df.columns]
                st.dataframe(filtered_df[display_cols], use_container_width=True)
        else:
            st.info("No BDE data available for charts.")

    with col_chart2:
        if 'PLAN' in filtered_df.columns and not filtered_df.empty:
            plan_counts = filtered_df['PLAN'].value_counts().reset_index()
            plan_counts.columns = ['PLAN', 'Count']
            fig_plan = px.pie(plan_counts, values='Count', names='PLAN', title='Plan Distribution', hole=0.3)
            st.plotly_chart(fig_plan, use_container_width=True)
        else:
            st.info("No Plan data available for charts.")

    # Timeline
    if 'Timestamp' in filtered_df.columns and not filtered_df.empty:
        daily_counts = filtered_df.groupby(filtered_df['Timestamp'].dt.date).size().reset_index(name='Count')
        fig_timeline = px.line(daily_counts, x='Timestamp', y='Count', title='Responses Over Time', markers=True)
        fig_timeline.update_layout(xaxis_title="Date", yaxis_title="Number of Responses")
        st.plotly_chart(fig_timeline, use_container_width=True)

    # Raw Data
    st.subheader("Raw Data")
    st.dataframe(filtered_df)

if __name__ == "__main__":
    main()
