
# A very simple Flask Hello World app for you to get started with...

# from flask import Flask, render_template
# import numpy as np
# import matplotlib
# matplotlib.use("Agg")
# import matplotlib.pyplot as plt
# import mpld3

################################################################################
#### FLASK #####################################################################
################################################################################

# app = Flask(__name__)
# app.config["DEBUG"] = True


# fig = plt.figure()
# ax = fig.add_subplot(111)
# ax.plot(range(100))
# mpld3.save_html(fig,'mysite/templates/fig.html')
# # fig.savefig("mysite/templates/graph.png")


# @app.route("/")
# def index():
#     # return render_template("main_page.html")
#     return render_template("fig.html")

################################################################################
#### DASH ######################################################################
################################################################################

# HELPFUL: https://dash.plotly.com/sharing-data-between-callbacks

from dash import Dash, html, dcc, callback, Output, Input
import plotly.express as px
import pandas as pd
import numpy as np
from model import format_loadshapes

app = Dash(__name__)

# PROCESS DATA
df = pd.read_csv('https://raw.githubusercontent.com/fhall18/powersupply/main/data/loadshape_finished.csv')
df_disaggregated = pd.read_csv('https://raw.githubusercontent.com/fhall18/powersupply/main/data/disaggregated_loadshapes.csv')
df_disaggregated.end_use = df_disaggregated.end_use.apply(lambda x: x.replace('_', ' '))

app.layout = html.Div([

    html.H1(children='Load Shape Extravaganza', style={'textAlign':'center','color':"#2AAA8A"}),
    html.Hr(),

    html.Div([
        html.Div([
            html.H4(children='Load Shape', style={'textAlign':'left'}),
            dcc.Checklist(
                        ['base', 'solar','ev'],
                        ['base'],
                        id='load--shape',
                        inline=True
                )],style={'width': '35%', 'display': 'inline-block'}),

        html.Div([
            html.H4(children='Flat Rate ($/kWh)', style={'textAlign':'left'}),
            dcc.Input(
            id="flat--rate",
            type="number",
            min=.05,
            max=.4,
            step=.005,
            value=0.16
            )],style={'width': '15%','float': 'center', 'display': 'inline-block'}),

        html.Div([
            html.H4(children='Peak Rate ($/kWh)', style={'textAlign':'left'}),
            dcc.Input(
            id="peak--rate",
            type="number",
            min=.2,
            max=.5,
            step=.005,
            value=0.2
            )],style={'width': '15%','float': 'center', 'display': 'inline-block'}),

        html.Div([
            html.H4(children='Off Peak Rate ($/kWh)', style={'textAlign':'left'}),
            dcc.Input(
            id="off--rate",
            type="number",
            min=.05,
            max=.15,
            step=.005,
            value=0.1
            )],style={'width': '15%','float': 'center', 'display': 'inline-block'}),
        ]),

    # SLIDER SECTION
    html.Div([
        html.Div([
            html.H4(children='Annual Base Electricity (kWh/year)', style={'textAlign':'left'}),
            dcc.Slider(5000,10000,step=1000,id='base--input',value=7000,)
            ],style={'width': '48%', 'display': 'inline-block'}),

        html.Div([
            html.H4(children='Solar Capacity (kW-AC)', style={'textAlign':'left'}),
            dcc.Slider(4,10,step=1,id='solar--input',value=6,)
            ],style={'width': '48%', 'float': 'right', 'display': 'inline-block'}),
    ]),

    # SLIDER SECTION
    html.Div([
        html.Div([
            html.H4(children='Peak Hours', style={'textAlign':'left'}),
            dcc.RangeSlider(1, 24, 1, value=[12, 20], id='peak--slider'),
            ],style={'width': '48%', 'display': 'inline-block'}),

        html.Div([
            html.H4(children='Miles Driven', style={'textAlign':'left'}),
            dcc.Slider(8000,15000,step=1000,id='miles--input',value=12000,)
            ],style={'width': '48%', 'float': 'right', 'display': 'inline-block'}),
    ]),

    html.Hr(),
    html.Div([
        # html.H1("Results from TOU Rate:"),
        # html.Br(),
        html.Div(id='result')
    ],style={"color": "#2AAA8A",'font-size': '22px','textAlign':'center'}),

    html.Hr(),

    # GRAPHS
    html.Div([
        dcc.Graph(
            id='graph-content',
            # hoverData={'points': [{'customdata': 'Japan'}]}
        )
    ], style={'width': '49%', 'display': 'inline-block', 'padding': '0 20'}),
    html.Div([
        dcc.Graph(id='peak-bar'),
        dcc.Graph(id='bubble-graph'),
    ], style={'display': 'inline-block', 'width': '49%'}),

])

################################################################################
##### CALLBACKS ################################################################
################################################################################

@callback(
    Output('result', 'children'),
    Input('flat--rate','value'),
    Input('peak--rate','value'),
    Input('off--rate','value'),
    Input('load--shape', 'value'), # new
    Input('base--input', 'value'),
    Input('solar--input','value'),
    Input('miles--input','value'),
    Input('peak--slider','value'))

def update_result(flat, peak, off,load,base,solar,miles,peakHours):

    dff = format_loadshapes(df,load,base,miles,solar,1000)
    peakHours = np.arange(min(peakHours),max(peakHours)+1,1)
    dff['peak'] = dff.hour.apply(lambda x: 'On-Peak' if x in peakHours else 'Off-Peak')

    dff = dff.groupby(['peak','end_use'],as_index=False).agg(energy = ('energy','sum'))

    load_names = set(dff.end_use)

    if 'everything' in load_names:
        df1 = dff[dff.end_use == 'everything']
    else:
        df1 = dff[dff.end_use == 'base']

    peak_kwh = sum(df1[df1.peak == 'On-Peak'].energy)
    off_peak_kwh = sum(df1[df1.peak == 'Off-Peak'].energy)
    total_kwh = sum(df1.energy)
    total_kwh_no_pv = sum(dff[dff.end_use != 'solar'].energy)

    tou_cost = peak_kwh * peak + off_peak_kwh * off
    flat_cost = total_kwh * flat

    tou_cost_kwh = np.round((tou_cost/total_kwh_no_pv),3)
    flat_cost_kwh = np.round(flat_cost/total_kwh,3)

    savings = np.round(flat_cost - tou_cost,2)

    return f"Flat: ${flat_cost_kwh}/kWh,     TOU: ${tou_cost_kwh}/kWh,     Annual Savings: ${savings}"

# NOTE: use Inputs in order for function...
@callback(
    Output('graph-content', 'figure'),
    Input('load--shape', 'value'),
    Input('flat--rate','value'),
    Input('peak--rate','value'),
    Input('off--rate','value'),
    Input('base--input', 'value'),
    Input('solar--input','value'),
    Input('miles--input','value'),
    Input('peak--slider','value')
    )

def update_graph(load,flat,peak,off,base,solar,miles,peakHours):
    # USE MILES

    dff = format_loadshapes(df,load,base,miles,solar,1000)

    # dff = df[df.end_use.isin(load)]

    # FIGURE
    fig = px.line(dff,
                x= 'time',
                y='energy',color='end_use')
    # fig.update_layout(legend=dict(yanchor="top", y=0.99,xanchor="left",x=0.01))

    fig.add_vrect(x0=min(peakHours), x1=max(peakHours),
              annotation_text="peak", annotation_position="top left",
              fillcolor="orange", opacity=0.25, line_width=0)

    fig.update_layout(legend=dict(
    title="Load Shape",
    orientation="h",
    yanchor="bottom",
    y=1.02,
    xanchor="right",
    x=1))
    fig.update_layout(margin={'l': 40, 'b': 40, 't': 10, 'r': 0}, hovermode='closest')
    fig.update_xaxes(title="Hourly")
    return fig

@callback(
    Output('bubble-graph', 'figure'),
    Input('load--shape', 'value'),
    Input('base--input', 'value'),
    Input('solar--input','value'),
    Input('miles--input','value'),
    Input('peak--slider','value'))

def update_bubble_graph(load,base,solar,miles,peakHours):

    # dff = format_loadshapes(df,load,base,miles,solar,1000)
    dff = df_disaggregated

    peak_hour_set = np.arange(min(peakHours),max(peakHours)+1,1)
    dff['peakHours'] = dff.hour.apply(lambda x: 1 if x in peak_hour_set else 0)

    #define conditions
    conditions = [(dff['peakHours'] == 1) & (dff['bd'] == True),
                  (dff['peakHours'] == 0) | (dff['bd'] == False)]

    results = ['on-peak', 'off-peak']     # define results
    dff['peak'] = np.select(conditions, results) # apply condition

    df_agg = dff.groupby(['end_use','category','peak'],as_index=False).agg(energy = ('energy','sum'))
    df_agg_pivot = df_agg.pivot(index = ['end_use','category'], columns='peak', values='energy').reset_index()

    df_agg_pivot['total'] = np.round(df_agg_pivot['off-peak'] + df_agg_pivot['on-peak'],0)
    df_agg_pivot['on-peak'] = np.round(df_agg_pivot['on-peak'],0)
    df_agg_pivot['peak_ratio'] = np.round(df_agg_pivot['on-peak']/df_agg_pivot['total'],3)

    fig = px.scatter(df_agg_pivot, x='total',y='on-peak',
                 size="peak_ratio", color="category", hover_name="end_use",
                 log_x=True, log_y=True, size_max=13)
    fig.update_layout(height=225, margin={'l': 20, 'b': 30, 'r': 10, 't': 10})
    fig.update_xaxes(title="Total Energy")
    fig.update_yaxes(title="Peak Energy")

    return fig



@callback(
    Output('peak-bar', 'figure'),
    Input('load--shape', 'value'),
    Input('base--input', 'value'),
    Input('solar--input','value'),
    Input('miles--input','value'),
    Input('peak--slider','value'))

def update_peak_bar(load,base,solar,miles,peakHours):

    dff = format_loadshapes(df,load,base,miles,solar,1000)
    peakHours = np.arange(min(peakHours),max(peakHours)+1,1)
    dff['peak'] = dff.hour.apply(lambda x: 'On-Peak' if x in peakHours else 'Off-Peak')

    dff = dff.groupby(['peak','end_use'],as_index=False).agg(energy = ('energy','sum'))
    dff.energy = np.round(dff.energy,0)

    fig = px.bar(dff, x='end_use', y='energy',color='peak')

    fig.update_layout(legend=dict(
    title="TOU",
    orientation="h",
    yanchor="bottom",
    y=1.02,
    xanchor="right",
    x=1),height=225, margin={'l': 20, 'b': 30, 'r': 10, 't': 10},
    xaxis={'categoryorder':'array', 'categoryarray':['base','solar','ev','everything']})

    fig.update_xaxes(title="")

    return fig

