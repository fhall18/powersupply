################################################################################
#### DASH ######################################################################
################################################################################

# HELPFUL: https://dash.plotly.com/sharing-data-between-callbacks

from dash import Dash, html, dcc, callback, Output, Input
import plotly.express as px
import plotly.io
import pandas as pd
import numpy as np
# from model import format_loadshapes
from engine import Rate

#external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = Dash(__name__,
        #external_stylesheets=external_stylesheets,
        meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1.0"}])
app.css.append_css({'external_url': 'reset.css'})

###
colors = {'background': '#111111', 'text': '#7FDBFF'}

# LOAD DATASETS
base = pd.read_csv('/home/thepowersupply/loadshapes/final_loadshapes.csv') # loadshape
base.datetime = pd.to_datetime(base.datetime)

rate = pd.read_csv('/home/thepowersupply/loadshapes/residential_rate_dataset.csv')

r1 = Rate(base,rate)
r2 = Rate(base,rate)

# r1.rateInfo('City of Burlington-Electric, Vermont (Utility Company) - Residential Service, Time-Of-Use (RT) Rate')
# r2.rateInfo('City of Burlington-Electric, Vermont (Utility Company) - Residential Service (Standard Residential Service)')


app.layout = html.Div([

    html.H1(children='Load Shape Extravaganza', style={'textAlign':'center','color':"#2AAA8A"}),
    html.H2(children='Developed by Freddie Hall', style={'textAlign':'center','color':"#FF4D00"}),
    html.Hr(),
    html.H3(children='What\'s this all about??',style={'textAlign':'left','color':"#2AAA8A"}),
    html.H3(dcc.Markdown('With +2/3 of our GHG emissions coming from how we use energy, \
    our primary goal should be to electrify our lives. After which, we should look to invest \
    in home power plants to power as much of our lives with local supply. \
    The objective is clear, but what will this cost, and can we leverage electric rates + \
    energy flexibility + solar for cost-effective energy decarbonization? This tool pulls \
    in +100k U.S. residential [electricity rates]( https://apps.openei.org/USURDB/) and builds \
    off a basic assumption that we use energy in predictable ways. Energy data is fueled by \
    hourly energy profiles ([thanks NREL]( https://www.nrel.gov/buildings/end-use-load-profiles.html)) \
    by climate region. I\'m writing an accompanying post that provides a bit more justification-juice \
    link coming soon. Also, a short disclaimer about this tool... this thing is a bit clunky and \
    hosted on a free server. I did my best to improve performance with efficient code/data structures \
    and limiting unnecessary callbacks, but there\'s a lot of data under the hood. Each adjustment \
    requires a good bit of number re-crunching. Take a deep breath before and while using. Slight \
    delays and potential crashes may be experienced as the Dash Minions work behind the scenes. \
    Please let me know what you think, love hearing feedback as your ideas/reactions make this \
    worthwhile. Also, try to break it and let me know what blows up. Always happy to chat!'),
    style={'textAlign':'left','color':"#69897D"}),
    html.H4(dcc.Markdown('[Github Repo](https://github.com/fhall18/powersupply/tree/main/loadshapes) \
    and some acronyms EV: electric vehicles, HP: heat pumps, HW: heat pump hot \
    water heaters, PV: photovoltaics or solar'),style={'textAlign':'left','color':"#69897D"}),


    # SELECTED LOADS
    html.Div([
        html.Hr(),

        html.Div([
            # SELECT UTILITY
            html.H4(children='Rate Comparison', style={'textAlign':'left'}),
            html.Div([
                # html.H4(children='Rate Selection', style={'textAlign':'left'}),
                dcc.Dropdown(rate.utility, id='utility--name',placeholder='SELECT ELECTRIC UTILITY',
                # value='City of Burlington-Electric, Vermont (Utility Company)'
                )],style={'width': '35%','float': 'center', 'display': 'inline-block'}),
            ]),
        ]),

        # RATE SELECTION
        html.Div([
            html.Div([
                html.H4(children='CURRENT RATE', style={'textAlign':'left'}),
                # html.H4(children='Rate Selection', style={'textAlign':'left'}),
                dcc.Dropdown(id='r1--rate',placeholder='SELECT CURRENT RATE',
                # value='City of Burlington-Electric, Vermont (Utility Company) - Residential Service, Time-Of-Use (RT) Rate'
                )],style={'width': '49%','float': 'left', 'display': 'inline-block'}),

            html.Div([
                html.H4(children='NEW RATE', style={'textAlign':'left'}),
                # html.H4(children='Peak Rate ($/kWh)', style={'textAlign':'left'}),
                dcc.Dropdown(id='r2--rate',placeholder='SELECT NEW RATE',
                # value = 'City of Burlington-Electric, Vermont (Utility Company) - Residential Service (Standard Residential Service)'
                )],style={'width': '49%','float': 'right', 'display': 'inline-block'})
            ]),

    # PERIOD
    html.Div([

        html.Div([
            html.H4(children='Energy Profile Graph', style={'textAlign':'left'}),
            dcc.RadioItems(
                        ['datetime','month','hour'],
                        value='hour',
                        id='period--input',
                        inline=False
                )],style={'width': '25%','float': 'left', 'display': 'inline-block'}),

        html.Div([
            html.H4(children='Load Shape', style={'textAlign':'left'}),
            dcc.Checklist(
                        options = ['base','ev','hp','hw','pv'],
                        value=['base'],
                        id='load--shape',
                        inline=True
                )],style={'width': '24%', 'display': 'inline-block'}),

        html.Div([
            html.H4(children='Climate', style={'textAlign':'left'}),
            dcc.RadioItems(
                        ['Very Cold','Cold','Hot-Dry','Hot-Humid','Marine'],
                        value='Cold',
                        id='climate--type',
                        inline=False
                )],style={'width': '35%', 'display': 'inline-block'}),

        html.Div([
            html.H4(children='Solar Value ($/kWh)', style={'textAlign':'left'}),
            dcc.Input(
                id="nm--value",
                type="number",
                min=.05,
                max=.25,
                step=.01,
                value=0.15
                )],style={'width': '10%','float': 'center', 'display': 'inline-block'}),
        ]),

    # SLIDER SECTION
    html.Div([
        html.Div([
            html.H4(children='Annual Base Electricity (kWh/year)', style={'textAlign':'left'}),
            dcc.Slider(5000,10000,step=1000,id='base--input',value=7000,)
            ],style={'width': '48%', 'display': 'inline-block'}),

        html.Div([
            html.H4(children='Solar Capacity (kW-AC)', style={'textAlign':'left'}),
            dcc.Slider(4,15,step=1,id='solar--input',value=7,)
            ],style={'width': '48%', 'float': 'right', 'display': 'inline-block'}),
    ]),

    # SLIDER SECTION
    html.Div([
        html.Div([
            html.H4(children='Avoided EV Charging Hours', style={'textAlign':'left'}),
            dcc.RangeSlider(1, 24, 1, value=[12, 20], id='peak--slider'),
            ],style={'width': '48%', 'display': 'inline-block'}),

        html.Div([
            html.H4(children='Miles Driven', style={'textAlign':'left'}),
            dcc.Slider(8000,15000,step=1000,id='miles--input',value=12000,)
            ],style={'width': '48%', 'float': 'right', 'display': 'inline-block'}),
    ]),

    # dcc.Store(id='intermediate-value'),

    html.Hr(),
    html.Div([
        # html.H1("Results from TOU Rate:"),
    #     # html.Br(),
        html.Div(id='result')
    ],style={"color": "#2AAA8A",'font-size': '22px','textAlign':'left'}),

    html.Hr(),

    # GRAPHS
    html.Div([

        dcc.Graph(
            id='wiggle-graph',
            figure={
                'layout': {
                    'plot_bgcolor': colors['background'],
                    'paper_bgcolor': colors['background'],
                    'font': {
                        'color': colors['text']
                        }
                    }
                }
            ),
        dcc.Graph(
            id='cost-graph',
                    figure={
            'layout': {
                'plot_bgcolor': colors['background'],
                'paper_bgcolor': colors['background'],
                'font': {
                    'color': colors['text']}
                }
            }
            # hoverData={'points': [{'customdata': 'Japan'}]}
        )
    ], style={'width': '49%', 'display': 'inline-block', 'padding': '0 20'}),

    html.Div([
        dcc.Graph(
            id='schedule1-graph',
            figure={
                'layout': {
                    'plot_bgcolor': colors['background'],
                    'paper_bgcolor': colors['background'],
                    'font': {
                        'color': colors['text']
                        }
                    }
                }
            ),
        dcc.Graph(
            id='schedule2-graph',
            figure={
                'layout': {
                    'plot_bgcolor': colors['background'],
                    'paper_bgcolor': colors['background'],
                    'font': {
                        'color': colors['text']
                        }
                    }
                }
        ),
    ], style={'display': 'inline-block', 'width': '49%'}),

])

################################################################################
##### CALLBACKS ################################################################
################################################################################

@callback(
    Output('r1--rate', 'options'),
    Input('utility--name', 'value'))

def set_r1_options(selected_utility):
    return [{'label': i, 'value': i} for i in rate[rate.utility == selected_utility].name]

@callback(
    Output('r2--rate', 'options'),
    Input('utility--name', 'value'))

def set_r2_options(selected_utility):
    return [{'label': i, 'value': i} for i in rate[rate.utility == selected_utility].name]


@callback(
    Output('wiggle-graph', 'figure'),
    Output('cost-graph','figure'),
    Output('result','children'),
    Input('utility--name', 'value'),
    Input('r1--rate', 'value'),
    Input('r2--rate', 'value'),
    Input('climate--type','value'),
    Input('load--shape','value'),
    Input('base--input', 'value'),
    Input('solar--input','value'),
    Input('miles--input','value'),
    Input('period--input','value'),
    Input('peak--slider','value'),
    Input('nm--value','value'))

def wiggle_graph(utility,r1Rate,r2Rate,climate,loadType,base,solar,miles,period,peak_slider,nm_value):
    r1Rate = utility + ' - ' + r1Rate
    r2Rate = utility + ' - ' + r2Rate

    # SELECT PROPER CLIMATIZE & LOAD(s)
    r1.climatize(climate,loadType)
    r2.climatize(climate,loadType) # do we need both?

    # ADJUST LOAD(S)
    r1.loadAdjustment(loadType,climate,base,solar,miles,peak_slider)
    r2.loadAdjustment(loadType,climate,base,solar,miles,peak_slider)

    # UPDATE RATE INFO
    r1.rateInfo(r1Rate,nm_value)
    r2.rateInfo(r2Rate,nm_value)

    # SAVINGS OUTPUT
    r1_cost = np.round(r1.totalCost/r1.totalEnergy,3)
    r2_cost = np.round(r2.totalCost/r2.totalEnergy,3)
    savings = np.round(r1.totalCost - r2.totalCost,0)
    if savings > 0:
        better_rate = 'New Rate'
    else: better_rate = 'Current Rate'
    savingsResults = f"Current: ${r1_cost}/kwh,     New: ${r2_cost}/kWh,      {better_rate} Savings: ${savings}"


    # WIGGLE FIGURE
    dff_ls = r1.loadshape.groupby([period,'type'],as_index=False).agg(energy = ('energy','sum'))

    fig = px.line(dff_ls, #r1.loadshape, #pd.concat([r1.rate,r2.rate]),
                x= period,
                y='energy',
                color ='type',
                template='plotly_white')

    fig.update_layout(legend=dict(yanchor="top", y=0.95,xanchor="left",x=0.01))

    fig.update_layout(legend=dict(
    title="Energy Profile:",
    orientation="h",
    yanchor="bottom",
    y=1.02,
    xanchor="right",
    x=1))
    fig.update_layout(height=245, margin={'l': 20, 'b': 30, 'r': 10, 't': 10})
    fig.update_xaxes(dtick="M1",tickformat="%b")
    if period == 'datetime':
        fig.update_xaxes(dtick="M1",tickformat="%b")
    # fig.update_xaxes(title="")

    # COST GRAPH
    dff = pd.concat([r1.rate,r2.rate])
    dff = dff.groupby(['month','rateNameShort'],as_index=False).agg(cost = ('cost','sum'))
    # FIGURE
    fig2 = px.line(dff,
                x= 'month',
                y='cost',
                color ='rateNameShort',
                template='plotly_white')

    fig2.update_layout(legend=dict(yanchor="top", y=0.95,xanchor="left",x=0.01))

    fig2.update_layout(legend=dict(title="Monthly Bill Impact",orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1))
    # fig.update_layout(margin={'l': 40, 'b': 40, 't': 10, 'r': 0}, hovermode='closest')
    fig2.update_layout(height=245, margin={'l': 20, 'b': 30, 'r': 10, 't': 10})
    fig2.update_xaxes(title="Month")
    fig2.update_yaxes(rangemode="tozero")

    return fig, fig2, savingsResults


# RATE SCHEDULE A
@callback(
    Output('schedule1-graph', 'figure'),
    Input('utility--name','value'),
    Input('r1--rate','value'),
    Input('nm--value','value'))

def update_rate_schedule_1(utility,r1Rate,nm_value):

    r1RateUtility = utility + ' - ' + r1Rate
    r1.rateInfo(r1RateUtility,nm_value)

    fig = px.imshow(r1.weekdayMatrixRate,
                labels=dict(x="Hour of Day", y="Month of Year", color="$/kWh"),
                x=['1','2','3','4','5','6','7','8','9','10','11','12','13','14','15','16','17','18','19','20','21','22','23','24'],
                y=['Jan', 'Feb', 'Mar','Apr', 'May', 'Jun','Jul', 'Aug', 'Sep','Oct', 'Nov', 'Dec']
               )

    fig.update_xaxes(side="top")
    fig.update_layout(
        height=245, margin={'l': 10, 'b': 20, 'r': 10, 't': 15},
        title=f"Current Rate: {r1Rate}",
        yaxis_title=None,
        xaxis_title=None,
        xaxis = dict(
            tickmode = 'array',
            tickvals = [6, 12, 18, 24],
            ticktext = ['6am', 'noon', '6pm', 'midnight']
            )
        )

    return fig

# RATE SCHEDULE B
@callback(
    Output('schedule2-graph', 'figure'),
    Input('utility--name','value'),
    Input('r2--rate', 'value'),
    Input('nm--value','value'))

def update_rate_schedule_2(utility,r2Rate,nm_value):

    r2RateUtility = utility + ' - ' + r2Rate
    r2.rateInfo(r2RateUtility,nm_value)

    fig = px.imshow(r2.weekdayMatrixRate,
                labels=dict(x="Hour of Day", y="Month of Year", color="$/kWh"),
                x=['1','2','3','4','5','6','7','8','9','10','11','12','13','14','15','16','17','18','19','20','21','22','23','24'],
                y=['Jan', 'Feb', 'Mar','Apr', 'May', 'Jun','Jul', 'Aug', 'Sep','Oct', 'Nov', 'Dec'])
    fig.update_xaxes(side="top")

    # fig.update_layout(legend=dict(
    #     title="TOU",
    #     orientation="h",
    #     yanchor="bottom",
    #     y=1.02,
    #     xanchor="right",
    #     x=1),height=225, margin={'l': 20, 'b': 30, 'r': 10, 't': 10},
    #     title=f"{r2Rate}")

    fig.update_layout(
        height=245, margin={'l': 20, 'b': 30, 'r': 10, 't': 15},
        title=f"New Rate: {r2Rate}",
        yaxis_title=None,
        xaxis_title=None,
        xaxis = dict(
            tickmode = 'array',
            tickvals = [6, 12, 18, 24],
            ticktext = ['6am', 'noon', '6pm', 'midnight']
            )
        )

    return fig
