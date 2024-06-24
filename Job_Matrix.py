import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Convert date columns to datetime
df['RQSTDTTM'] = pd.to_datetime(df['RQSTDTTM'])
df['BEGINDTTM'] = pd.to_datetime(df['BEGINDTTM'])
df['ENDDTTM'] = pd.to_datetime(df['ENDDTTM'])

# Calculate durations and request to begin time
df['DURATION'] = (df['ENDDTTM'] - df['BEGINDTTM']).dt.total_seconds() / 60  # Convert to minutes
df['UPGRADE'] = df['RQSTDTTM'] >= pd.Timestamp('2024-05-19')

# Aggregate to weekly intervals
df.set_index('BEGINDTTM', inplace=True)
weekly_avg = df.groupby(['PRCSNAME', pd.Grouper(freq='W')])['DURATION'].mean().reset_index()
weekly_avg['UPGRADE'] = weekly_avg['BEGINDTTM'] >= pd.Timestamp('2024-05-19')

# Separate pre and post-upgrade data
pre_upgrade = weekly_avg[weekly_avg['UPGRADE'] == False]
post_upgrade = weekly_avg[weekly_avg['UPGRADE'] == True]

# Calculate IQR
pre_iqr = pre_upgrade.groupby('PRCSNAME')['DURATION'].apply(lambda x: x.quantile(0.75) - x.quantile(0.25)).reset_index(name='IQR_Pre')
post_iqr = post_upgrade.groupby('PRCSNAME')['DURATION'].apply(lambda x: x.quantile(0.75) - x.quantile(0.25)).reset_index(name='IQR_Post')

# Merge pre and post-upgrade IQR data
comparison_iqr = pd.merge(pre_iqr, post_iqr, on='PRCSNAME', suffixes=('_Pre', '_Post'))
comparison_iqr['Difference (minutes)'] = comparison_iqr['IQR_Post'] - comparison_iqr['IQR_Pre']
comparison_iqr['Improvement (%)'] = (comparison_iqr['Difference (minutes)'] / comparison_iqr['IQR_Pre']) * -100
comparison_iqr['Change'] = comparison_iqr['Difference (minutes)'].apply(lambda x: 'Improvement' if x < 0 else 'Regression' if x > 0 else 'No Change')

# Sort by improvement/regression
comparison_iqr = comparison_iqr.sort_values('Difference (minutes)')

# Create subplots layout
fig = make_subplots(
    rows=3, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.03,
    specs=[[{"type": "table"}],
           [{"type": "scatter"}],
           [{"type": "scatter"}]]
)

# Add table trace
fig.add_trace(
    go.Table(
        header=dict(
            values=["Job Name", "IQR Pre-Upgrade (minutes)", "IQR Post-Upgrade (minutes)", 
                    "Difference (minutes)", "Improvement (%)"],
            font=dict(size=10),
            align="left"
        ),
        cells=dict(
            values=[comparison_iqr[k].tolist() for k in comparison_iqr.columns],
            align="left")
    ),
    row=1, col=1
)

# Add scatter plot trace
scatter_fig = px.scatter(comparison_iqr, x='IQR_Pre', y='IQR_Post', color='Change',
                         title='IQR of Job Durations Pre vs. Post Upgrade',
                         labels={'IQR_Pre': 'IQR Pre-Upgrade (minutes)', 'IQR_Post': 'IQR Post-Upgrade (minutes)'},
                         hover_data=['PRCSNAME', 'Difference (minutes)', 'Improvement (%)'])

# Add line of equality (y=x) to show no change
scatter_fig.add_shape(
    type='line',
    line=dict(dash='dash'),
    x0=0, y0=0,
    x1=comparison_iqr['IQR_Pre'].max(),
    y1=comparison_iqr['IQR_Pre'].max()
)

for trace in scatter_fig['data']:
    fig.add_trace(trace, row=2, col=1)

# Function to create a time series plot
def create_time_series(dff, title):
    fig = px.line(dff, x='BEGINDTTM', y='DURATION', title=title)
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)
    fig.update_layout(margin={'l': 20, 'b': 30, 'r': 10, 't': 10})
    return fig

# Add a time series plot for the most improved job
most_improved_job = comparison_iqr.iloc[0]['PRCSNAME']
dff = weekly_avg[weekly_avg['PRCSNAME'] == most_improved_job]
time_series = create_time_series(dff, f'<b>{most_improved_job}</b><br>Duration over Time')

for trace in time_series['data']:
    fig.add_trace(trace, row=3, col=1)

# Update layout
fig.update_layout(
    height=1200,
    showlegend=False,
    title_text="Job Performance Dashboard",
    hovermode='closest'
)

# Add dropdown menu for job selection to update the time series plot
dropdown_buttons = [
    dict(label=job, method="update", args=[
        {"visible": [True]*len(fig.data)},
        {"title": f'<b>{job}</b><br>Duration over Time'}
    ]) for job in comparison_iqr['PRCSNAME'].unique()
]

fig.update_layout(
    updatemenus=[
        dict(
            buttons=dropdown_buttons,
            direction="down",
            showactive=True,
            x=0.17,
            xanchor="left",
            y=1.1,
            yanchor="top"
        )
    ]
)

# Save as interactive HTML
fig.write_html("job_matrix_performance_dashboard.html")

print("Dashboard saved as 'job_matrix_performance_dashboard.html'")
