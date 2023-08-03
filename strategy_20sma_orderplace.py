import time
import pandas as pd
import numpy as np
from datetime import timedelta, datetime
import urllib
from breeze_connect import BreezeConnect

api_key='XXXXX'
api_secret='XXXXX'
session_token=17513184

STOCK = 'GAIL'
PERIOD = 20
MARKET_CLOSE = datetime.now().replace(hour=19,minute=25,second=0,microsecond=0)
#data = []

print("https://api.icicidirect.com/apiuser/login?api_key="+urllib.parse.quote_plus(api_key))

# Initialize SDK
api = BreezeConnect(api_key=api_key)
api.generate_session(api_secret=api_secret,session_token=session_token)
#Connect to websocket(it will connect to tick-by-tick data server)
api.ws_connect()

# Global variable to store the current_price
current_price = None
current_position = None

# Callback to receive ticks.
def on_ticks(ticks):
    global current_price
    #print("Ticks: {}".format(ticks))
    current_price = ticks['last']
    print(f'current_price : {current_price}')


# Assign the callbacks.
api.on_ticks = on_ticks

current_time = datetime.now().strftime("%H:%M:%S")
print(f'current time : {current_time}')
print ("Starting websockets --> ",current_time, "\n")

# subscribe to underlying
api.subscribe_feeds(exchange_code="NSE", 
                          stock_code=STOCK, 
                          product_type="cash", 
                          get_exchange_quotes=True, 
                          get_market_depth=False)

# Function to calculate SMA
def get_sma():
    now = datetime.now()
    from_date = now - timedelta(days=1) # calculate last 30 days SMA
    current_time = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')  # Update current_time inside the function
    try :
        data = api.get_historical_data_v2(interval='1minute',
                                          from_date=from_date.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                                          to_date=current_time,
                                          stock_code=STOCK,
                                          exchange_code="NSE",
                                          product_type="cash")
        if(data['Status']==200):
            # Calculate the SMA of Close Price
            data = pd.DataFrame(data['Success'])
            data = data[['datetime','close']]
            data.close = data.close.astype(float)
            sma = round(data.close.rolling(PERIOD).mean(),2)
            print(f'sma : {sma}')
            return sma.iloc[-1]
            
        elif(data['Status']==500):
            print('Bad API Request : ',data)
            return None
    except Exception as error:
        print('Failed API request', error)
        return None

THRESHOLD = get_sma()
print(f'THRESHOLD : {THRESHOLD}')


# Function to generate signal
def signal(current_price, sma):
    print(f'current_price: {current_price} | SMA : {THRESHOLD}')
    if sma is None:
        return None  # Return None if SMA is not available
    elif current_price > sma:
        return "buycall"
    elif current_price < sma:
        return "buyput"
    else:
        return None

# Function to place buy order
def place_buy_order():
    global current_price
    try:
        order_response = api.place_order(
            stock_code=STOCK,
            exchange_code="NSE",
            product="cash",
            action="buy",
            order_type="market",
            #right="call",  # For Call option
            #strike_price=call_strike,
            quantity="1",  # Specify the quantity you want to buy
            price=current_price,  # Use the 5-minute 'close' price from the current row in the 'df_subset' DataFrame
            validity="day"
            #expiry_date="2023-08-31T07:00:00.000Z"
        )
        print("Buy order placed successfully:", order_response)
    except Exception as error:
        print("Failed to place buy order:", error)

# Function to place sell order
def place_sell_order():
    global current_price
    try:
        order_response = api.place_order(
            stock_code=STOCK,
            exchange_code="NSE",
            product="cash",
            action="sell",
            order_type="market",
            #right="call",  # For Call option
            #strike_price=call_strike,
            quantity="1",  # Specify the quantity you want to buy
            price=current_price,  # Use the 5-minute 'close' price from the current row in the 'df_subset' DataFrame
            validity="day"
            #expiry_date="2023-08-31T07:00:00.000Z"
        )
        print("Sell order placed successfully:", order_response)
    except Exception as error:
        print("Failed to place sell order:", error)

# Time function to control entry and exit time of strategy
def timer():
    global current_price,current_position
    while datetime.now() < MARKET_CLOSE:
        print(f'Time : {datetime.now().strftime("%H:%M:%S")} ... Strategy is Live ')
        
        # Get the signal
        if current_price is not None and THRESHOLD is not None and not np.isnan(current_price):
            sma = THRESHOLD
            signal_type = signal(current_price, sma)
        
        # Place orders based on the signal
        # Place orders based on the signal and current position
            if signal_type == "buycall" and current_position != "buycall":
                place_buy_order(1)  # You can set the desired quantity for buy order
                current_position = "buycall"
            elif signal_type == "buyput" and current_position != "buyput":
                place_sell_order(1)  # You can set the desired quantity for sell order
                current_position = "buyput"

        time.sleep(5)

    print('Closing socket')
    # Unsubscribe stocks feeds
    api.unsubscribe_feeds(exchange_code="NSE", 
                          stock_code=STOCK, 
                          product_type="cash", 
                          get_exchange_quotes=True, 
                          get_market_depth=False)
    api.ws_disconnect()

# start timer
timer()
