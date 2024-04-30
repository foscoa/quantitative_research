
import numpy as np
import calendar

import matplotlib
import plotly.graph_objects as go
import seaborn as sns
from dash import Dash, html, dcc, dash_table
from dash.dash_table import FormatTemplate
from plotly.subplots import make_subplots

from utils.query_mongoDB_functions import *

# database connection
url = "mongodb+srv://foscoa:Lsw0r4KyI0rlq8YH@cluster0.vu31vch.mongodb.net/"
client = pymongo.MongoClient(url)


# QUERY ETFs ----

db = client['ETFs']
collection = db['Yahoo_Finance']

print(client.list_database_names())

start = '2014-01-02'
end = '2024-03-31'
tickers = ['SPY', 'VIXY', 'SVXY', '^VIX']
param = "Open"

ETFs = q_TS_ETFs(tickers=tickers,
               start=start,
               end=end,
               param=param,
               collection=collection)

# QUERY VIX Futures ----

db = client.Listed_Futures
collection = db.CBOE_VIX_Futures_monthly
start = '2013-01-02'
end = '2024-03-31'
# Project only the "Open" and "Date" fields
projection = {"_id": 0, "Futures": 1, 'Expiry': 1}

# Execute the query
futures_map = pd.DataFrame(list(collection.find({}, projection))).drop_duplicates().sort_values(by='Expiry')

contracts = list(futures_map.Futures)


tot_vol = q_TS_VIX_futures(contracts=contracts,
                      start=start,
                      end=end,
                      param='Total Volume',
                      collection=collection)

tot_vol = tot_vol[list(futures_map.Futures)] # order by maturity

# Open
param = 'Open'

open = q_TS_VIX_futures(contracts=contracts,
                      start=start,
                      end=end,
                      param=param,
                      collection=collection)

open = open[list(futures_map.Futures)] # order by maturity


# QUERY Future interpol

db = client.Listed_Futures
collection = db.CBOE_VIX_Futures_monthly_INT
vix_int = q_TS_VIX_futures_INT(start=start,
                           end=end,
                           param=param,
                           collection=collection)

# merging
data = pd.merge(ETFs, vix_int, left_index=True, right_index=True, how='left')
data.columns = data.columns.str.replace(" ", "_").to_list()
# strategy LSV
starting_capital = 100000
pct_risk = 0.5
allocation =starting_capital*pct_risk

# long position in SVXY
data['LSV_SVXY'] = (allocation/data.SVXY).astype(int)*(data.month_1-data.VIX > 2).astype(int)

# long position in VIXY
data['LSV_VIXY'] = (allocation/data.VIXY).astype(int)*(data.month_1-data.VIX < -2).astype(int)

# PnL
data['LSV_PnL'] = (data.SVXY.shift(-1) - data.SVXY)*data.LSV_SVXY + (data.VIXY.shift(-1) - data.VIXY)*data.LSV_VIXY
data['LSV_PnL'] = data['LSV_PnL'].fillna(0)

#cumsum
data['LSV_cum_PnL'] = data.LSV_PnL.cumsum()

class BacktestTradingStrategy:
    def __init__(self,
                 name: str,
                 description: str,
                 asset_prices,
                 starting_capital = np.nan,
                 benchmark      = np.nan,
                 signal         = np.nan):

        # run validations to the received arguments
        assert asset_prices.index.equals(signal.index), "The input - asset_prices - (with the first " \
                                                            "row deleted) and the input - signal - do not " \
                                                            "have the same indices."

        assert asset_prices.index.equals(benchmark.index), "The input - asset_prices - (with the first " \
                                                               "row deleted) and the input - benchmark - do not " \
                                                               "have the same indices."

        # assign to self object
        self.name = name
        self.description = description
        self.asset_prices = asset_prices
        self.starting_capital = starting_capital
        self.benchmark = benchmark
        self.signal = signal

    def assets_daily_PnL(self):

        # PnL is from t to T+1
        PnL = (self.asset_prices.shift(-1) - self.asset_prices) * self.signal
        PnL = PnL.fillna(0)

        return PnL

    def portfolio_daily_PnL(self):

        return pd.DataFrame(data=self.assets_daily_PnL().sum(axis=1),
                            columns=['Portfolio'])

    def portfolio_value(self):

        return self.portfolio_daily_PnL().cumsum() + self.starting_capital

    def portfolio_daily_returns(self):
        portfolio_cumulative_returns = pd.DataFrame(
            data=self.portfolio_value().shift(-1) / self.portfolio_value() - 1,
            columns=['Portfolio'])
        portfolio_cumulative_returns.fillna(0, inplace=True)
        return portfolio_cumulative_returns

    def benchmark_daily_returns(self):

        bm = self.benchmark.shift(-1) / self.benchmark - 1

        bm_cumulative_returns = pd.DataFrame(data=bm)
        bm_cumulative_returns.fillna(0, inplace=True)
        bm_cumulative_returns.columns = ["Benchmark"]
        return bm_cumulative_returns

    def portfolio_monthly_returns(self):
        # monthly returns
        monthly_returns = {}

        portfolio_value = self.portfolio_value()

        for year in portfolio_value.index.year.unique():
            PT_cum_ret_year = portfolio_value[portfolio_value.index.year == year]
            for month in PT_cum_ret_year.index.month.unique():
                PT_cum_ret_month = PT_cum_ret_year[PT_cum_ret_year.index.month == month]
                monthly_returns[calendar.month_abbr[month] + "-" + str(year)] = \
                    PT_cum_ret_month['Portfolio'][-1] / PT_cum_ret_month['Portfolio'][0] - 1

        return monthly_returns

    def portfolio_yearly_returns(self):
        # development ground
        PT_cum_ret = self.portfolio_value()
        YTD_returns = {}

        for year in PT_cum_ret.index.year.unique():
            PT_cum_ret_year = PT_cum_ret[PT_cum_ret.index.year == year]

            YTD_returns["YTD-" + str(year)] = \
                PT_cum_ret_year['Portfolio'][-1] / PT_cum_ret_year['Portfolio'][0] - 1

        return YTD_returns

    def strategy_monthly_returns_table(self):
        # develop
        PT_cum_ret = self.portfolio_value()
        monthy_returns_table = pd.DataFrame(data=[],
                                            columns=calendar.month_abbr[1:13] + ["YTD"],
                                            index=PT_cum_ret.index.year.unique()[::-1])

        for year in PT_cum_ret.index.year.unique():
            PT_cum_ret_year = PT_cum_ret[PT_cum_ret.index.year == year]
            monthy_returns_table["YTD"][year] = PT_cum_ret_year['Portfolio'][-1] / PT_cum_ret_year['Portfolio'][0] - 1
            for month in PT_cum_ret_year.index.month.unique():
                PT_cum_ret_month = PT_cum_ret_year[PT_cum_ret_year.index.month == month]
                monthy_returns_table[calendar.month_abbr[month]][year] = \
                    PT_cum_ret_month['Portfolio'][-1] / PT_cum_ret_month['Portfolio'][0] - 1

        return monthy_returns_table

    def drawdown(self):

        PT_cum_ret = self.portfolio_value() / self.starting_capital -1
        DD = (PT_cum_ret - PT_cum_ret.cummax())

        return DD

    def cagr(self):

        PT_cum_ret = self.portfolio_value() / self.starting_capital

        days = PT_cum_ret.index[-1] - PT_cum_ret.index[0]
        years = days.days/365

        cagr = (float(PT_cum_ret.values[-1])**(1/years))-1

        return cagr

    def calculate_summary_statistics(self):

        summary_stat = {}

        PT_daily_returns = self.portfolio_daily_returns()

        PT_excess_returns = pd.DataFrame(PT_daily_returns['Portfolio'])

        summary_stat["ann. mean"] = float(PT_daily_returns.mean().values) * 252
        summary_stat["ann. std"] = float(PT_daily_returns.std().values) * np.sqrt(252)
        summary_stat["max DD"] = float(self.drawdown().min().values)
        summary_stat["sharpe ratio"] = float(PT_excess_returns.mean().values)*252/\
                                       (float(PT_daily_returns.std().values) * np.sqrt(252))
        summary_stat["CAGR"] = self.cagr()

        return summary_stat

    def generate_report(self):

        # benchmark
        BM_cum_log_returns = (self.benchmark_daily_returns() + 1).cumprod()

        # portfolio returns
        PT_returns = (self.portfolio_daily_returns() + 1).cumprod()

        fig = make_subplots(rows=2,
                            cols=1,
                            shared_xaxes=True,
                            vertical_spacing=0.02,
                            row_heights=[0.8, 0.2]
                            )

        fig.add_trace(
            go.Scatter(
                x=PT_returns.index.to_list(),
                y=PT_returns['Portfolio'].to_list(),
                line_color='cadetblue',
                name='Strategy'
            ),
            row=1,
            col=1)

        fig.add_trace(
            go.Scatter(
                x=BM_cum_log_returns.index.to_list(),
                y=BM_cum_log_returns['Benchmark'].to_list(),
                line_color='tan',
                name='S&P500'
            ),
            row=1,
            col=1)

        fig.add_trace(
            go.Scatter(
                x=self.drawdown().index.to_list(),
                y=self.drawdown()['Portfolio'].to_list(),
                fill='tozeroy',
                line_color="darkred",
                name='Drawdown'
            ),
            row=2,
            col=1)

        fig.update_yaxes(tickformat='.2%',
                         row=2,
                         col=1)

        fig.update_layout(
            title=strategy.name + "<br>"
                  + "<sub>"
                  + "CAGR = " + str(round(self.calculate_summary_statistics()['CAGR'] * 100, 2)) + "%,   "
                  + "mean p.a. = " + str(round(self.calculate_summary_statistics()['ann. mean'] * 100, 2)) + "%,   "
                  + "std p.a. = " + str(round(self.calculate_summary_statistics()['ann. std'] * 100, 2)) + "%,   "
                  + "max DD = " + str(round(self.calculate_summary_statistics()['max DD'] * 100, 2)) + "%,   "
                  + "sharpe ratio = " + str(round(self.calculate_summary_statistics()['sharpe ratio'], 2)) +

                  " </sub>" +

                  "<br>",

            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )

        return fig

    def generate_dash_monthly_returns_table(self):

        my_df = self.strategy_monthly_returns_table()
        my_df.insert(0, 'Year', my_df.index)
        percentage = FormatTemplate.percentage(2)

        n_palette = 40
        min_color = -0.3
        max_color = 0.3

        master_palette = [matplotlib.colors.to_hex(color) for color in
                          sns.diverging_palette(h_neg=10, h_pos=120, l=50, s=100, n=n_palette + 1, as_cmap=False)]

        filter = np.linspace(start=min_color, stop=max_color, num=len(master_palette) - 1)
        filter = np.insert(filter, 0, -1)
        filter = np.append(filter, 10)

        return dash_table.DataTable(
                    data=my_df.to_dict('records'),
                    columns=[{'id': my_df.columns[0], 'name': my_df.columns[0]}] +
                            [{'id': c, 'name': c, 'type': 'numeric', 'format': percentage} for c in my_df.columns[1:]],
                    css=[{'selector': 'table', 'rule': 'table-layout: fixed'}],
                    style_cell={
                        'width': '{}%'.format(len(my_df.columns))
                    },
                    style_data_conditional=[
                        {
                            'if': {
                                'column_id': 'YTD'
                            },
                            'fontWeight': 'bold',
                            'border-left': 'double'
                        },
                        {
                            'if': {
                                'column_id': 'Year'
                            },
                            'fontWeight': 'bold',
                            'border-right': 'double'
                        },

                    ] + [
                        {
                            'if': {
                                'filter_query': '{'+ j +'} > ' + str(filter[i]) + ' && {'+ j +'} < ' + str(filter[i+1])
                                                + ' && {' + j + '} !=0',
                                'column_id': j},
                            'backgroundColor': str(master_palette[i])
                        } for i in range(0, n_palette+1) for j in strategy.strategy_monthly_returns_table().columns
                    ]


                )


asset_prices = data[['VIXY', 'SVXY']]
signal = data[['LSV_VIXY', 'LSV_SVXY']]
signal.columns = ['VIXY', 'SVXY']
starting_capital = 100000
benchmark = data.SPY

# Define Strategy instance
strategy = BacktestTradingStrategy(
    name='LSV',
    description='Long-Short VIX',
    asset_prices=asset_prices,
    benchmark=benchmark,
    signal=signal,
    starting_capital=starting_capital
)

# APP

app = Dash(__name__)

# app
app.layout = html.Div(
    children=[

        html.Div(
            children=[
                dcc.Graph(
                    id='example-graph',
                    figure=strategy.generate_report(),
                    style= {'height': '70vh'}
                ),
            ],
            style={'height': '70vh'}
        ),

        html.Div(
            children=[
                strategy.generate_dash_monthly_returns_table()
            ],
            style={'marginLeft': 80, 'marginRight': 120}
        ),

])

if __name__ == '__main__':
    app.run_server(debug=False, port=5000)






