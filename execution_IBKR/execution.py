from ib_async import *
import pandas as pd
import time

while(1>0):

    ib = IB()
    ib.connect('127.0.0.1', 7496, clientId=1)

    list = ib.accountSummary()
    print('Margin data saved as of ' + time.asctime())
    account_summary = pd.DataFrame([item for item in list if (item.tag == 'InitMarginReq') or (item.tag == 'MaintMarginReq')])

    ib.disconnect()

    time.sleep(10)