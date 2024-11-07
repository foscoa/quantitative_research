import calendar
import numpy as np
from plotly.subplots import make_subplots
import pandas as pd
import matplotlib
import plotly.graph_objects as go
import seaborn as sns
from dash import dash_table
from dash.dash_table import FormatTemplate

class BacktestTradingStrategy:
    def __init__(self,
                 name: str,
                 description: str,
                 asset_prices,
                 starting_capital = np.nan,
                 benchmark      = np.nan,
                 signal         = np.nan,
                 transaction_costs = np.nan):

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
        self.transaction_costs = transaction_costs

    def assets_daily_PnL(self):

        # PnL is from t to T+1
        PnL = (self.asset_prices.shift(-1) - self.asset_prices) * self.signal
        PnL = PnL.fillna(0)

        return PnL

    def portfolio_daily_PnL(self):

        PnL = self.assets_daily_PnL().sum(axis=1) - self.transaction_costs

        return pd.DataFrame(data=PnL,
                            columns=['Portfolio'])

    def portfolio_value(self):

        PT_val = self.portfolio_daily_PnL().shift(1).cumsum() + self.starting_capital
        PT_val.iloc[0] = self.starting_capital
        PT_val[PT_val <= 0] = 0

        return PT_val

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

    def monthly_returns_table(self):

        # benchmark name
        bm_name = self.benchmark.columns[0]

        PT_cum_ret = self.portfolio_value()
        monthy_returns_table = pd.DataFrame(data=[],
                                            columns=calendar.month_abbr[1:13] + ["Strategy"] + [bm_name],
                                            index=PT_cum_ret.index.year.unique()[::-1])

        # Portfolio
        for year in PT_cum_ret.index.year.unique():
            PT_cum_ret_year = PT_cum_ret[PT_cum_ret.index.year == year]
            monthy_returns_table["Strategy"][year] = PT_cum_ret_year['Portfolio'][-1] / PT_cum_ret_year['Portfolio'][0] - 1
            for month in PT_cum_ret_year.index.month.unique():
                PT_cum_ret_month = PT_cum_ret_year[PT_cum_ret_year.index.month == month]
                monthy_returns_table[calendar.month_abbr[month]][year] = \
                    PT_cum_ret_month['Portfolio'][-1] / PT_cum_ret_month['Portfolio'][0] - 1

        # Benchmark
        bm = self.benchmark
        for year in bm.index.year.unique():
            BM_cum_ret_year = bm[bm.index.year == year]
            monthy_returns_table[bm_name][year] = BM_cum_ret_year[bm_name][-1] / BM_cum_ret_year[bm_name][0] - 1

        return monthy_returns_table

    def drawdown(self):

        PT_cum_ret = self.portfolio_value() / self.starting_capital
        DD = (PT_cum_ret / PT_cum_ret.cummax() - 1)

        return DD.shift(-1)

    def cagr(self):

        PT_cum_ret = self.portfolio_value() / self.starting_capital

        days = PT_cum_ret.index[-1] - PT_cum_ret.index[0]
        years = days.days/365

        cagr = (float(PT_cum_ret.values[-1])**(1/years))-1

        return cagr

    def correlation_with_benchmark(self):

        # building dataframe
        df = self.benchmark_daily_returns()
        df['PT'] = self.portfolio_daily_returns()

        return df.corr().iloc[0, 1]

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
        summary_stat["corr"] = self.correlation_with_benchmark()

        return summary_stat

    def cumulative_return_plot(self):

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
                name=self.benchmark.columns[0]
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
            title=self.name + "<br>"
                  + "<sub>"
                  + "CAGR = " + str(round(self.calculate_summary_statistics()['CAGR'] * 100, 2)) + "%,   "
                  + "mean p.a. = " + str(round(self.calculate_summary_statistics()['ann. mean'] * 100, 2)) + "%,   "
                  + "std p.a. = " + str(round(self.calculate_summary_statistics()['ann. std'] * 100, 2)) + "%,   "
                  + "max DD = " + str(round(self.calculate_summary_statistics()['max DD'] * 100, 2)) + "%,   "
                  + "sharpe ratio = " + str(round(self.calculate_summary_statistics()['sharpe ratio'], 2)) + ",   "
                  + "corr = " + str(round(self.correlation_with_benchmark(), 2)) +

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

    def dash_monthly_returns_table(self):

        my_df = self.monthly_returns_table()
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
                    columns=[{'id': my_df.columns[0], 'name': ["Monthly Returns (%)", my_df.columns[0]]}] +
                            [{'id': c, 'name': ["Monthly Returns (%)", c], 'type': 'numeric', 'format': percentage} for c in my_df.columns[1:-2]] +
                            [{'id': c, 'name': ["Annual Returns", c], 'type': 'numeric', 'format': percentage} for c in my_df.columns[-2:]],
                    css=[{'selector': 'table', 'rule': 'table-layout: fixed'}],
                    style_data_conditional=[
                        {
                            'if': {
                                'column_id': 'Strategy'
                            },
                            'fontWeight': 'bold',
                            'border-left': 'double',
                            'width': '{}%'.format(len(my_df.columns))
                        },
                        {
                            'if': {
                                'column_id':  "SPY"
                            },
                            'fontWeight': 'bold',
                            'width': '{}%'.format(len(my_df.columns))
                        },
                        {
                            'if': {
                                'column_id': 'Year'
                            },
                            'fontWeight': 'bold',
                            'border-right': 'double',
                            'width': '{}%'.format(len(my_df.columns))
                        },


                    ] + [
                        {
                            'if': {
                                'filter_query': '{'+ j +'} > ' + str(filter[i]) + ' && {'+ j +'} < ' + str(filter[i+1])
                                                + ' && {' + j + '} !=0',
                                'column_id': j},
                            'backgroundColor': str(master_palette[i]),
                            'width': '{}%'.format(len(my_df.columns))
                        } for i in range(0, n_palette+1) for j in self.monthly_returns_table().columns[:-2]
                    ],
                    style_header={
                        'textAlign': 'left'
                    },
                    merge_duplicate_headers=True


                )

    def trailing_returns_table(self):
        # Define a function to calculate the cumulative return over a specified period
        def calculate_return(df, period):
            start_date = df.index.max() - pd.DateOffset(
                months=period) if period != 'since_inception' else df.index.min()
            end_date = df.index.max()

            col_name = df.columns[0]

            if period == 'since_inception':
                return (df.loc[end_date, col_name] / df.loc[start_date, col_name]) - 1

            try:
                start_value = df[df.index >= start_date].iloc[0][col_name]
                end_value = df.loc[end_date, col_name]
                return (end_value / start_value) - 1
            except IndexError:
                return None  # In case there are not enough data points for the period requested

        # some variables
        pt_value = self.portfolio_value()
        bm_value = self.benchmark
        percentage = FormatTemplate.percentage(2)

        trailing_returns = []

        # Calculate returns for the required periods
        # 1 month
        trailing_returns.append({'Time period':'Last month', 'Strategy': calculate_return(pt_value, period=1),
                                         bm_value.columns[0]: calculate_return(bm_value, period=1)})

        # 3 months
        trailing_returns.append({'Time period':'3 months','Strategy': calculate_return(pt_value, period=3),
                                          bm_value.columns[0]: calculate_return(bm_value, period=3)})

        # 6 months
        trailing_returns.append({'Time period':'6 months','Strategy': calculate_return(pt_value, period=6),
                                            bm_value.columns[0]: calculate_return(bm_value, period=6)})

        # 1 year
        trailing_returns.append({'Time period':'1 year','Strategy': calculate_return(pt_value, period=12),
                                            bm_value.columns[0]: calculate_return(bm_value, period=12)})

        # 18 months
        trailing_returns.append({'Time period':'18 months', 'Strategy': calculate_return(pt_value, period=18),
                                      bm_value.columns[0]: calculate_return(bm_value, period=18)})

        # 2 years
        trailing_returns.append({'Time period':'2 years', 'Strategy': calculate_return(pt_value, period=24),
                                      bm_value.columns[0]: calculate_return(bm_value, period=24)})

        # 3 years
        trailing_returns.append({'Time period':'3 years', 'Strategy': calculate_return(pt_value, period=36),
                                      bm_value.columns[0]: calculate_return(bm_value, period=36)})

        # 5 years
        trailing_returns.append({'Time period':'5 years','Strategy': calculate_return(pt_value, period=60),
                                       bm_value.columns[0]: calculate_return(bm_value, period=60)})

        # Since inception
        trailing_returns.append({'Time period':'Since inception', 'Strategy': calculate_return(pt_value, period='since_inception'),
                                       bm_value.columns[0]: calculate_return(bm_value, period='since_inception')})



        return dash_table.DataTable(
                    data=trailing_returns,
                    columns=[{"name": 'Time period', "id": 'Time period'}] +
                            [{"name": i, "id": i, 'type': 'numeric', 'format': percentage} for i in ['Strategy', bm_value.columns[0]]],
        )