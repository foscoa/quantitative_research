import backtrader as bt
import yfinance as yf

class SmaCross(bt.Strategy):
    params = (("short_period", 10), ("long_period", 30),)

    def __init__(self):
        # Define short and long SMAs
        self.short_sma = bt.indicators.SimpleMovingAverage(self.data.close, period=self.params.short_period)
        self.long_sma = bt.indicators.SimpleMovingAverage(self.data.close, period=self.params.long_period)

    def next(self):
        # Check for crossover
        if self.short_sma > self.long_sma and not self.position:  # Golden cross
            self.buy()
        elif self.short_sma < self.long_sma and self.position:  # Death cross
            self.sell()

# Create a cerebro instance
cerebro = bt.Cerebro()

# Add the strategy
cerebro.addstrategy(SmaCross)

# Fetch historical data from Yahoo Finance
data = bt.feeds.PandasData(dataname=yf.download("AAPL", "2020-01-01", "2021-01-01"))

# Add the data to cerebro
cerebro.adddata(data)

# Set initial capital
cerebro.broker.setcash(10000)

# Set commission
cerebro.broker.setcommission(commission=0.001)

# Run the backtest
print(f"Starting Portfolio Value: {cerebro.broker.getvalue():.2f}")
cerebro.run()
print(f"Ending Portfolio Value: {cerebro.broker.getvalue():.2f}")

# Plot the results
cerebro.plot()
