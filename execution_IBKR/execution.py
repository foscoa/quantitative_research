from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.utils import iswrapper
import pandas as pd

import threading
import time
from scipy import interpolate
from datetime import datetime
from dateutil.relativedelta import relativedelta
import numpy as np


class IBapi(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.vix_data = {}
        self.vix_df = pd.DataFrame(columns=["Symbol", "Price"])

    @iswrapper
    def error(self, reqId, errorCode, errorString):
        print("Error: ", reqId, " ", errorCode, " ", errorString)

    @iswrapper
    def tickPrice(self, reqId, tickType, price, attrib):
        if tickType == 4:  # Last price
            self.vix_data[reqId] = price
            print("VIX Future:", reqId, "Price:", price)
            self.vix_df.loc[reqId] = [self.expiries[reqId], price]

    def create_vix_contract(self, localSymbol):
        # Create contract object
        contract = Contract()
        contract.localSymbol = localSymbol
        contract.currency = "USD"

        if contract.localSymbol == 'VIX':
            contract.secType = "IND"
            contract.exchange = "CBOE"
        else:
            contract.secType = "FUT"
            contract.exchange = "CFE"


        return contract

    def start(self, expiries):
        self.expiries = expiries
        for i, expiry in enumerate(expiries):
            contract = self.create_vix_contract(expiry)
            self.reqMktData(i, contract, "", False, False, [])

def main():

    app = IBapi()
    app.connect("127.0.0.1", 7496, 0)

    # Start the socket in a thread
    api_thread = threading.Thread(target=app.run, daemon=True)
    api_thread.start()

    time.sleep(1)  # Sleep to allow connection time

    # Request market data for VIX futures
    vix_localSymbols = ['VIX',
                        'VXQ4',
                        'VXU4',
                        'VXV4',
                        'VXX4',
                        'VXZ4',
                        'VXF5',
                        'VXG5',
                        #'VXH5'
                        ]
    expiries = [datetime.today().strftime("%Y%m%d"),
                '20240821',
                '20240918',
                '20241016',
                '20241120',
                '20241218',
                '20250122',
                '20250222',
                # '20250318'
                ]
    app.start(vix_localSymbols)

    time.sleep(10)  # Sleep to allow time for data to be fetched
    app.disconnect()

    # Save the term structure
    vix_ts = app.vix_df
    vix_ts['expiry'] = expiries

    return vix_ts

if __name__ == "__main__":
    a = main()

# generate term structure
# cublic spline
today = datetime.today()

x = np.array([datetime.strptime(exp, "%Y%m%d").toordinal() for exp in a.expiry])
y = np.array(a.Price)
cs = interpolate.CubicSpline(x, y)

# Add one month to today's date
next_month = today + relativedelta(months=1)

vix_1m = cs(np.array(next_month.toordinal()))


