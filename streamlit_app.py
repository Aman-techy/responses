import streamlit as st
import pandas as pd
import plotly.express as px

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
    
    if st.sidebar.button("Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    # Apply Filters
    filtered_df = df.copy()
    if selected_bde != 'All BDEs':
        filtered_df = filtered_df[filtered_df['BDE NAME'] == selected_bde]
    
    if selected_plan != 'All Plans':
        filtered_df = filtered_df[filtered_df['PLAN'] == selected_plan]

    # Metrics
    total_responses = len(filtered_df)
    total_closed_amount = filtered_df['CLOSED AMOUNT'].sum() if 'CLOSED AMOUNT' in filtered_df.columns else 0

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Responses", total_responses)
    with col2:
        st.metric("Total Closed Amount", f"₹{total_closed_amount:,.2f}")

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
