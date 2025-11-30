import dash
from dash import dcc, html, dash_table, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd

# URL for the Google Sheet CSV export
SHEET_URL = "https://docs.google.com/spreadsheets/d/1PIhDB-RqQguZl6kGb19_ZkXcVvMYJwMmflgaiZ0PDDQ/export?format=csv"

def load_data():
    try:
        df = pd.read_csv(SHEET_URL)
        # Clean column names
        df.columns = df.columns.str.strip()
        
        # Convert Timestamp to datetime
        if 'Timestamp' in df.columns:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
            
        # Convert CLOSED AMOUNT to numeric
        if 'CLOSED AMOUNT' in df.columns:
            df['CLOSED AMOUNT'] = pd.to_numeric(df['CLOSED AMOUNT'], errors='coerce').fillna(0)
            
        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
server = app.server

# Initial data load for dropdown options
df_initial = load_data()
bde_options = [{'label': 'All BDEs', 'value': 'ALL'}]
plan_options = [{'label': 'All Plans', 'value': 'ALL'}]

if not df_initial.empty:
    if 'BDE NAME' in df_initial.columns:
        bdes = sorted(df_initial['BDE NAME'].dropna().unique().tolist())
        bde_options += [{'label': bde, 'value': bde} for bde in bdes]
    
    if 'PLAN' in df_initial.columns:
        plans = sorted(df_initial['PLAN'].dropna().unique().tolist())
        plan_options += [{'label': plan, 'value': plan} for plan in plans]

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H1("Response Visualizer", className="text-center text-primary mb-4"), width=12)
    ]),

    # Filters
    dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Filter by BDE:"),
                    dcc.Dropdown(
                        id='bde-filter',
                        options=bde_options,
                        value='ALL',
                        clearable=False
                    )
                ], md=4),
                dbc.Col([
                    html.Label("Filter by Plan:"),
                    dcc.Dropdown(
                        id='plan-filter',
                        options=plan_options,
                        value='ALL',
                        clearable=False
                    )
                ], md=4),
                dbc.Col([
                    html.Br(),
                    dbc.Button("Refresh Data", id='refresh-btn', color="success", className="w-100")
                ], md=4)
            ])
        ])
    ], className="mb-4"),

    # Metrics
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Total Responses", className="card-title text-center"),
                    html.H2(id='total-responses', className="text-center text-info")
                ])
            ])
        ], md=6),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Total Closed Amount", className="card-title text-center"),
                    html.H2(id='total-amount', className="text-center text-success")
                ])
            ])
        ], md=6),
    ], className="mb-4"),

    # Charts
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Graph(id='bde-graph')
                ])
            ])
        ], md=6),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Graph(id='plan-graph')
                ])
            ])
        ], md=6),
    ], className="mb-4"),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Graph(id='timeline-graph')
                ])
            ])
        ], width=12)
    ], className="mb-4"),

    # Data Table
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Raw Data"),
                dbc.CardBody([
                    dash_table.DataTable(
                        id='data-table',
                        page_size=10,
                        style_table={'overflowX': 'auto'},
                        style_cell={'textAlign': 'left'},
                        style_header={
                            'backgroundColor': 'rgb(230, 230, 230)',
                            'fontWeight': 'bold'
                        }
                    )
                ])
            ])
        ], width=12)
    ])

], fluid=True, className="p-4")

@app.callback(
    [Output('total-responses', 'children'),
     Output('total-amount', 'children'),
     Output('bde-graph', 'figure'),
     Output('plan-graph', 'figure'),
     Output('timeline-graph', 'figure'),
     Output('data-table', 'data'),
     Output('data-table', 'columns')],
    [Input('bde-filter', 'value'),
     Input('plan-filter', 'value'),
     Input('refresh-btn', 'n_clicks')]
)
def update_dashboard(selected_bde, selected_plan, n_clicks):
    # Reload data on refresh or initial load
    df = load_data()
    
    if df.empty:
        return "0", "₹0.00", {}, {}, {}, [], []

    # Apply Filters
    if selected_bde != 'ALL':
        df = df[df['BDE NAME'] == selected_bde]
    
    if selected_plan != 'ALL':
        df = df[df['PLAN'] == selected_plan]

    # Metrics
    total_responses = len(df)
    total_closed_amount = df['CLOSED AMOUNT'].sum() if 'CLOSED AMOUNT' in df.columns else 0
    
    # 1. BDE Performance (Bar Chart)
    if 'BDE NAME' in df.columns and not df.empty:
        bde_metrics = df.groupby('BDE NAME').agg({
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
    else:
        fig_bde = px.bar(title="No Data Available")

    # 2. Plan Distribution (Pie Chart)
    if 'PLAN' in df.columns and not df.empty:
        plan_counts = df['PLAN'].value_counts().reset_index()
        plan_counts.columns = ['PLAN', 'Count']
        fig_plan = px.pie(plan_counts, values='Count', names='PLAN', title='Plan Distribution', hole=0.3)
    else:
        fig_plan = px.pie(title="No Data Available")

    # 3. Timeline (Line Chart)
    if 'Timestamp' in df.columns and not df.empty:
        daily_counts = df.groupby(df['Timestamp'].dt.date).size().reset_index(name='Count')
        fig_timeline = px.line(daily_counts, x='Timestamp', y='Count', title='Responses Over Time', markers=True)
        fig_timeline.update_layout(xaxis_title="Date", yaxis_title="Number of Responses")
    else:
        fig_timeline = px.line(title="No Data Available")

    # Table Columns
    columns = [{'name': i, 'id': i} for i in df.columns]
    
    return (
        f"{total_responses}",
        f"₹{total_closed_amount:,.2f}",
        fig_bde,
        fig_plan,
        fig_timeline,
        df.to_dict('records'),
        columns
    )

if __name__ == '__main__':
    app.run(debug=True)
