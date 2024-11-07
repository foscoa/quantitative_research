from dash import Dash, html, dcc

def generate_factsheet_app(strategy):

    app = Dash(__name__)

    # app
    app.layout = html.Div(
        children=[

            html.Div(
                children=[
                    dcc.Graph(
                        id='example-graph',
                        figure=strategy.cumulative_return_plot(),
                        style={'width': '100%', 'height': '100%'}
                    ),
                ],
                style={'width': '100%', 'height': '70vh', 'display': 'flex'}
            ),

            html.Div(
                children=[
                    strategy.dash_monthly_returns_table()
                ],
                style={'marginLeft': 80, 'marginRight': 80}
            ),

        ])

    return app