import os, time
from datetime import datetime
import pandas as pd
import json
import telepot
import finnhub
#from finnhub import client as Finnhub
from telepot.loop import MessageLoop

here = os.path.dirname(os.path.realpath(__file__))
config_path = here + "/input_data/"

with open(os.path.join(config_path,'config.json'),'r') as s: config = json.load(s)
#client = Finnhub.Client(api_key=config['finnhub_api_key'])  #print (config['finnhub_api_key'])
bot = telepot.Bot(config['Telegram_key'])  #print (config['Telegram_key'])
chat_id = config['Telegram_chat_id']

chat_list = []
for item in chat_id:
    ##print (str(item['id']))
    chat_list.append(str(item['id']))

#print(purchases_path)
df_purchases = pd.read_csv((config_path+"purchases_example.csv"), header='infer')
df_purchases['cost'] = df_purchases['quantity']*df_purchases['price_pence']
df_purchases['name'] = df_purchases['name'].str.upper()
df_purchases['ticker'] = df_purchases['ticker'].str.upper()

df_summary = df_purchases.groupby(['ticker','name']) \
    .agg(purchase_count=('quantity','size'),total_quantity = ('quantity','sum') ,total_cost = ('cost','sum'),average_cost = ('cost','sum'), currency = ('currency','max')) \
    .reset_index()
df_summary['avg_unit_price'] = df_summary['total_cost']/df_summary['total_quantity']
df_summary['timestamp'] = 0
##print(df_summary)

def finnhub_price(share_symbol):
    from finnhub import client as Finnhub
    client = Finnhub.Client(api_key=config['finnhub_api_key'])
    price = client.quote(symbol = share_symbol)
    ##print("api_call")
    return price


def update_all(ticker):
    for index, row in df_summary.iterrows():
        ##print(index)
        if row["ticker"] == ticker:
            price = finnhub_price(row['ticker']) #client.quote(symbol= row['ticker'])
            df_summary.at[index,'current_price'] = price['c']
            df_summary.at[index,'timestamp'] = price['t']
            df_summary.at[index,'prev_close'] = price['pc']
            ##print("got ticker data")
        elif ticker == "ALL":
            ##print("testing if up to date")
            if pd.to_datetime(row["timestamp"],unit='s') + pd.DateOffset(hours=2) < datetime.now():
                price = finnhub_price(row['ticker']) #price = client.quote(symbol= row['ticker'])
                df_summary.at[index,'current_price'] = price['c']
                df_summary.at[index,'timestamp'] = price['t']
                df_summary.at[index,'prev_close'] = price['pc']
                ##print("retrieved data")
            #else:               
                ##print("data_up_to_date")
            price = finnhub_price(row['ticker']) #client.quote(symbol= row['ticker'])
            df_summary.at[index,'current_price'] = price['c']
            df_summary.at[index,'timestamp'] = price['t']
            df_summary.at[index,'prev_close'] = price['pc']


    df_summary['time'] = pd.to_datetime(df_summary['timestamp'], unit='s')
    df_summary['current_value'] = df_summary['current_price']*df_summary['total_quantity']
    df_summary['day_change'] = (df_summary['current_price'] - df_summary['prev_close']) * df_summary['total_quantity'] 
    
    #df_summary['total_cost'] = df_summary['currency'].apply(lambda x: 79 if x == 'USD' else 1) * df_summary['total_cost']
    #df_summary['current_value'] = df_summary['currency'].apply(lambda x: 79 if x == 'USD' else 1) * df_summary['current_value']
    #df_summary['total_cost'] = np.where(df['currency'] = 'USD', df_summary['total_cost'] * 0.79, df_summary['total_cost'])

    #total_cost = df_summary['total_cost'].sum()/100
    #current_value = df_summary['current_value'].sum()/100
    #total_perc_change =  100*(current_value - total_cost) / total_cost
    ##print(df_summary)
    
    if ticker == 'ALL':
        search_term = '.*' #'RegExp\\=*'
    else:
        search_term = ticker
    #message = ticker + ": Total cost: £"+ str("{:,.2f}".format(df_summary["total_cost"].sum()))
    #"\nCurrent value: £" + str("{:,.2f}".format(current_value)) + \
    #"\nP/L: £" + str("{:,.2f}".format(current_value-total_cost)) + \
    #"\nAPI count: "
    #print (summary)
    #print(message)
    
    #else:
    #    ticker = "RegExp\\=*" 
    pl = df_summary[df_summary["ticker"].str.match(search_term)]["current_value"].sum() - df_summary[df_summary["ticker"].str.match(search_term)]["total_cost"].sum()
    perc_chg = 100*( (df_summary[df_summary["ticker"].str.match(search_term)]["current_value"].sum() / df_summary[df_summary["ticker"].str.match(search_term)]["total_cost"].sum()) - 1)
    day_perc = 100*( df_summary[df_summary["ticker"].str.match(search_term)]["day_change"].sum() / df_summary[df_summary["ticker"].str.match(search_term)]["current_value"].sum() )
    ##print(ticker)
    total_value = ticker + ": Value: £" + str("{:.2f}".format(df_summary[df_summary["ticker"].str.match(search_term)]["current_value"].sum()/100)) + " change of " +  str("{:.2f}".format(perc_chg)) + "%" + \
    "\nOrig cost: £" + str("{:.2f}".format(df_summary[df_summary["ticker"].str.match(search_term)]["total_cost"].sum()/100)) + " P/L: £" + str("{:.2f}".format(pl/100))
    day_change = "\nChange today: £" + str("{:.2f}".format(df_summary[df_summary["ticker"].str.match(search_term)]["day_change"].sum()/100)) + " Move of: " + str("{:.2f}".format(day_perc)) + "%"


    message = total_value + day_change
        #"\nAvg purchase price is : " + str("{:.2f}".format(ticker_average_cost)) + "p, a " + str("{:.2f}".format(ticker_perc_change)) + "perc change"  + \
        #"\nAvg purchase price is : " + str("{:.2f}".format(ticker_average_cost)) + \
        #"\nTotal cost: £"+ str("{:,.2f}".format(total_cost)) + \
        #"\nCurrent value: £" + str("{:,.2f}".format(ticker_current_value)) + \
        #"\nP/L: £" + str("{:,.2f}".format(ticker_current_value - ticker_total_cost)) + \
        #"\nAPI count: "
        #print (df_summary)
    #message = "hi"
    return message


def handle(msg):
    ##print(msg)
    content_type, chat_type, chat_id = telepot.glance(msg)
    command = msg['text']
    ##print(content_type, chat_type, chat_id, command)
    ##print (df_summary['ticker'])

    if content_type == 'text' and str.lower(command) == "help" and str(chat_id) in chat_list:
        message_back = "Please type 'all' to see result against all shares and 'list' to see individual shares/funds"
        bot.sendMessage(chat_id, message_back)
    elif content_type == 'text' and str.lower(command) == "list" and str(chat_id) in chat_list:
        message_back = ""
        for index, row in df_summary.iterrows():
            message_back = message_back + "\n" + row["ticker"] +" / " + row["name"]
        ##message_back = "Please type 'ALL' to see result against all shares"
        bot.sendMessage(chat_id, message_back)

    elif content_type == 'text' and str.upper(command) == "ALL" and str(chat_id) in chat_list:
        message_back = update_all(str.upper(command))
        bot.sendMessage(chat_id, message_back)
    
    elif content_type == 'text' and str.upper(command) in (name.upper() for name in df_summary['ticker']) and str(chat_id) in chat_list:
        message_back = update_all(str.upper(command))
        bot.sendMessage(chat_id, message_back)

    elif content_type == 'text' and str.upper(command) in (name.upper() for name in df_summary['name']) and str(chat_id) in chat_list:
        tick = df_summary[df_summary["name"] == str.upper(command)]["ticker"].iloc[0]
        #print(tick)
        #bot.sendMessage(chat_id, tick)
        message_back = update_all(str.upper(tick))
        bot.sendMessage(chat_id, message_back)

    else:
        message_back = "Command not recognised, please send 'help' to understand supported commands"
        bot.sendMessage(chat_id, message_back)

MessageLoop(bot, handle).run_as_thread() #timeout = 10)

##print('Listening...')
bot.sendMessage(487208758, "Service initialised and running...")

#update_all()
#exit()
while 1:
    try:
        time.sleep(20)
        #exit()
    
    except KeyboardInterrupt:
        ##print('\n Program interrupted')
        exit()
    
    except:
        ##print('Other error or exception occured!')
        exit()
