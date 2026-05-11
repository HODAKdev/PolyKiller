# Made by Hodak, 2026
# Version 0.0.1

# polymarket
from py_clob_client.clob_types import (
    OrderArgs,
    PartialCreateOrderOptions,
    BalanceAllowanceParams,
    AssetType,
    MarketOrderArgs,
    OrderType,
)
from py_clob_client.client import ClobClient
from py_clob_client.exceptions import PolyApiException


# idk
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from dotenv import load_dotenv
from zoneinfo import ZoneInfo
from time import sleep
import websockets
import concurrent
import threading
import requests
import argparse
import asyncio
import random
import pickle
import signal
import json
import time
import sys
import os
import re

# plot
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# web3
from web3 import Web3
from web3.constants import MAX_INT
from web3.middleware import ExtraDataToPOAMiddleware

# ????
CTF_ABI = '[{"inputs":[{"name":"conditionId","type":"bytes32"}],"name":"payoutDenominator","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"name":"conditionId","type":"bytes32"},{"name":"index","type":"uint256"}],"name":"payoutNumerators","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]'
ERC1155_ABI = '[{"inputs":[{"name":"account","type":"address"},{"name":"id","type":"uint256"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]'
REDEEM_ABI = '[{"inputs":[{"name":"collateralToken","type":"address"},{"name":"parentCollectionId","type":"bytes32"},{"name":"conditionId","type":"bytes32"},{"name":"indexSets","type":"uint256[]"}],"name":"redeemPositions","outputs":[],"stateMutability":"nonpayable","type":"function"}]'
REDEEM_ABI_CHECK = '[{"inputs":[{"name":"collateralToken","type":"address"},{"name":"parentCollectionId","type":"bytes32"},{"name":"conditionId","type":"bytes32"},{"name":"indexSets","type":"uint256[]"}],"name":"redeemPositions","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"bytes32","name":"conditionId","type":"bytes32"}],"name":"payoutDenominator","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]'

# filled from .env file
POLYMARKET_CLIENT = None
W3_CLIENT = None
WALLETS_TO_COPY = None
POLYGON_RPC = None
POLYGON_WSS = None
PUBLIC_KEY = None
PRIVATE_KEY = None
FIXED = None
MIN = None
MAX = None
SCALE = None
MODE = None
RATIO_FOR_TRADE = None
ENABLE_TRADING = None
ORDER_TYPE = None
SHARES = None
RUN_BACKTEST_FILE = None
RUN_BACKTEST_URL = None
REDEEM_POSITIONS = None
BACKTEST_BALANCE = None
BACKTEST_LIMIT = None
MAX_SLIPPAGE = None
REDEEM_COOLDOWN = None
LIMIT_PRICE = None
ENABLE_COPY_TRADE = None
ENABLE_TEST1 = None
SAMPLES = None
THRESHOLD = None
WAIT_TIME = None
FUNDER_PUBLIC_KEY = None
WIN_PROFIT_THRESHOLD = None
ENABLE_BTC = None
ENABLE_ETH = None
ENABLE_SOL = None
ENABLE_XRP = None
ENABLE_DOGE = None
TRADER_MIN = None
TRADER_MAX = None
MIN_TRADER_AMOUNT = None
MAX_DUPLICATE_POSITIONS = None
BLOCK_SELL_POSITIONS = None
USE_YOUR_AMOUNT_BACKTEST = None
ENABLE_OTHER_MARKETS = None
USE_WORSE_ENTRY = None
USE_WORSE_PNL = None
MAX_DUPLICATE_POSITIONS_SLUG = None
USE_LIMIT_ORDERS = None
FILTER_TRADES_BY_TITLE = None
ALLOWED_HOURS = None
FILTER_TRADES_BY_YOUR_TRADES = None
AUTO_FIND_BY_LEADBOARD = None
LEADBOARD_CATEGORY = None
LEADBOARD_TIME_PERIOD = None
LEADBOARD_LIMIT = None
WALLETS_TO_COPY_2 = None
SKIP_NOT_PROFIT_WALLETS = None
ONLY_ONE_ORDER = None
RETRY_COUNT = None

BTC_UPDOWN_5M = "btc-updown-5m"
ETH_UPDOWN_5M = "eth-updown-5m"
SOL_UPDOWN_5M = "sol-updown-5m"
XRP_UPDOWN_5M = "xrp-updown-5m"
DOGE_UPDOWN_5M = "doge-updown-5m"

# file data
DATA = []
DATA_FILENAME = "data.json"
DATA_FILENAME_BIN = "data.bin"

last_redeem = 0
lock = threading.Lock()
lock_balance = threading.Lock()
last_balance = 0
redeem_list = {}

class Trade:
    def __init__(self):
        self.tx_hash = ""
        self.from_hash = ""
        self.to_hash = ""
        self.token_id = ""
        self.slug = ""
        self.side_str = ""
        self.amount = 0
        self.your_amount = 0
        self.win_price = 0
        self.utc = None
        self.error = None
        self.order = None
        self.printed = False
        self.timex = ""
        self.price = 0
        self.last_liq = 0
        self.side = ""
        self.trading_enabled = False
        self.redeemed = False
        self.closed = False
        self.condition_id = None
        self.title = ""

    def debug(self):
        if self.error:
            print(f"* Error: {self.error}")
            return

        print(f"* TX:            {self.tx_hash}")
        print(f"* From:          {self.from_hash}")
        print(f"* To:            {self.to_hash}")
        print(f"* Token ID:      {self.token_id}")
        print(f"* Condition ID:  {self.condition_id}")
        print(f"* Slug:          {self.slug}")
        print(f"* Outcome:       {self.side_str}")
        print(f"* Side:          {self.side}")
        print(f"* Trader amount: {self.amount:.2f} USDC")
        print(f"* UTC:           {self.utc}")
        print(f"* Price:         {self.price} ({(self.price * 100):.2f} USDC)")
        print(f"* Your amount:   {self.your_amount:.2f} USDC")
        # print(f"* You can win: {self.win_price:.2f} USDC")
        print(f"* Delay:         {self.timex}")
        print(f"* Liquidity:     {self.last_liq:.2f} USDC")
        print("---")

trades = []




# datetime
def str_to_datetime(s: str):
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
def datetime_to_str(dt: datetime):
    return dt.strftime("%Y-%m-%d %H:%M:%S")
def get_utc_from_timestamp(timestamp):
    # 1773827100
    dt_utc = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return dt_utc
def get_dt_from_string(text):
    # 2026-03-18 09:45:00+00:00
    dt = datetime.fromisoformat(text)
    return dt
def get_timestamp_from_datetime(dt):
    return int(dt.timestamp())
def get_timestamp_from_slug(slug):
    return int(slug.split("-")[-1])
def get_utc_time():
    return datetime.now(timezone.utc)
def floor_minutes_to_nearest_5(dt):
    minutes = dt.minute
    floored = (minutes // 5) * 5
    return dt.replace(minute=floored, second=0, microsecond=0)
def subtract_5_minutes(dt):
    return dt - timedelta(minutes=5)

# helpers
def pretty_print(data):
    print(json.dumps(data, indent=4, sort_keys=True))
def get_env_value(value):
    return os.getenv(value)
def is_worth_trading(win_price: float, amount: float, min_profit_ratio: float):
    x = win_price >= amount * (1 + min_profit_ratio)
    return x
def to_usdc(amount: int):
    return amount / 1e6
def calc_amount(trade_amount: float, min_amt: float, max_amt: float, trader_max: float):
    ratio = trade_amount / trader_max
    amount = ratio * max_amt
    return round(max(min_amt, min(amount, max_amt)), 2)
def save_data(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)
def load_data(filename):
    datax = None

    try:
        with open(filename, "r") as f:
            datax = json.load(f)
    except FileNotFoundError:
        datax = []

    return datax
def get_scaled_pnl(entry, price, my_investment):
    trader_invested = price * entry["totalBought"]

    if trader_invested == 0:
        return 0

    ratio = my_investment / trader_invested
    return entry["realizedPnl"] * ratio
def generate_id():
    return random.randint(0, 9)
def get_winner(up_price, down_price):
    if up_price > 0.9:
        return 0
    elif down_price > 0.9:
        return 1
    else:
        return None
def contains_word(text: str, word: str):
    return word.lower() in text.lower()
def save_data_bin(filename, data):
    with open(filename, "wb") as f:
        pickle.dump(data, f)
def load_data_bin(filename):
    try:
        with open(filename, "rb") as f:
            return pickle.load(f)
    except FileNotFoundError:
        return []
def load_trades(filename):
    global trades

    raw = load_data(filename)
    trades_data = []
    for d in raw:
        t = Trade()
        t.__dict__.update(d)
        trades_data.append(t)
    
    trades = trades_data
def save_trades(filename):
    datax = [t.__dict__ for t in trades]
    save_data(DATA_FILENAME, datax)
def get_trade_by_token_id(token_id: str, side: str):
    for trade in trades:
        if trade.token_id == token_id:
            if trade.side.lower() == side.lower():
                return trade

    return None
def get_win_price(price, amount: float):
    if price:
        return round(float(amount) / price, 2)

    return None
def adjust_price(price, worsening_pct):
    return price * (1 - worsening_pct / 100)

# blockchain
def get_balance():
    resp = requests.post(POLYGON_RPC, json={
        "jsonrpc": "2.0", "id": 1,
        "method": "eth_call",
        "params": [{
            "to": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174", # usdc
            "data": "0x70a08231000000000000000000000000" + PUBLIC_KEY[2:]
        }, "latest"]
    }).json()
    return int(resp["result"], 16) / 1e6
def get_token_transfers(wallet: str):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "alchemy_getAssetTransfers",
        "params": [{
            "fromBlock": "0x0",
            "toBlock": "latest",
            "toAddress": wallet,
            "contractAddresses": ["0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"],  # USDC
            "category": ["erc20"],
            "withMetadata": True
        }]
    }
    r = requests.post(POLYGON_RPC, json=payload)
    return r.json()["result"]["transfers"]
def get_total_deposited(wallet: str):
    POLYMARKET_CTF = "0x4bfb41d5b3570defd03c39a9a4d8de6bd8b8982e"
    POLYMARKET_REDEEM = "0x4d97dcd97ec945f40cf65f87097ace5ea0476045"
    
    transfers = get_token_transfers(wallet)
    total = 0.0
    for tx in transfers:
        from_addr = tx["from"].lower()
        if from_addr not in [POLYMARKET_CTF, POLYMARKET_REDEEM]:
            amount = float(tx["value"])
            total += amount
            # print(f"Deposit: ${amount:.2f} from {from_addr}")
    return total

# web3
def init_w3():
    global W3_CLIENT
    W3_CLIENT = Web3(Web3.HTTPProvider(POLYGON_RPC))
    W3_CLIENT.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)



def can_redeem(condition_id: str):
    try:
        ctf = W3_CLIENT.eth.contract(
            address=W3_CLIENT.to_checksum_address("0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"),
            abi=REDEEM_ABI_CHECK
        )
        condition_id_bytes = bytes.fromhex(condition_id[2:])
        # payoutDenominator > 0 means resolved
        payout = ctf.functions.payoutDenominator(condition_id_bytes).call()
        return payout > 0
    except Exception:
        return False
def redeem_position(condition_id: str):
    ctf = W3_CLIENT.eth.contract(
        address=W3_CLIENT.to_checksum_address("0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"),
        abi=REDEEM_ABI
    )

    nonce = W3_CLIENT.eth.get_transaction_count(W3_CLIENT.to_checksum_address(PUBLIC_KEY), "pending")

    tx = ctf.functions.redeemPositions(
        W3_CLIENT.to_checksum_address("0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"),
        b'\x00' * 32,
        bytes.fromhex(condition_id[2:]),
        [1, 2]
    ).build_transaction({
        "chainId": 137,
        "from": PUBLIC_KEY,
        "nonce": nonce,
        "maxFeePerGas": W3_CLIENT.to_wei(200, "gwei"),
        "maxPriorityFeePerGas": W3_CLIENT.to_wei(50, "gwei"),
    })

    signed = W3_CLIENT.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
    sent = W3_CLIENT.eth.send_raw_transaction(signed.raw_transaction)
    receipt = W3_CLIENT.eth.wait_for_transaction_receipt(sent, 600)

    return receipt
def is_winner_old(token_id: str):
    ctf = W3_CLIENT.eth.contract(
        address=W3_CLIENT.to_checksum_address("0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"),
        abi=CTF_ABI
    )

    resp = get_market_info_from_token_id(token_id)
    condition_id = resp[0].get("conditionId", "")
    condition_bytes = bytes.fromhex(condition_id[2:])
    
    denominator = ctf.functions.payoutDenominator(condition_bytes).call()
    if denominator == 0:
        return False
    
    numerator_0 = ctf.functions.payoutNumerators(condition_bytes, 0).call()
    numerator_1 = ctf.functions.payoutNumerators(condition_bytes, 1).call()
    
    outcome = resp[0].get("outcome", "").lower()
    
    if outcome == "yes" or outcome == "up":
        return numerator_1 > 0
    else:
        return numerator_0 > 0

def need_to_redeem(token_id: str):
    ctf = W3_CLIENT.eth.contract(
        address=W3_CLIENT.to_checksum_address("0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"),
        abi=ERC1155_ABI
    )
    balance = ctf.functions.balanceOf(
        W3_CLIENT.to_checksum_address(PUBLIC_KEY),
        int(token_id)
    ).call()
    
    return balance > 0

# polymarket
def get_closed_trades(limit, offset):
    # by date new to old
    data = requests.get(f"https://data-api.polymarket.com/closed-positions?user={WALLETS_TO_COPY}&limit={limit}&offset={offset}&sortBy=TIMESTAMP&sortDirection=DESC").json()
    return data
def get_closed_trades2(limit):
    all_data = []
    offset = 0
    batch_size = 50

    while len(all_data) < limit:
        data = get_closed_trades(batch_size, offset)

        if not data:
            break

        all_data.extend(data)

        if len(data) < batch_size:
            break

        offset += batch_size

    return all_data[:limit]
def get_market_info(slug):
    return requests.get(f"https://gamma-api.polymarket.com/markets?slug={slug}").json()
def get_event_info(slug):
    return requests.get(f"https://gamma-api.polymarket.com/events?slug={slug}").json()
def get_activity(limit, offset):
    return requests.get(f"https://data-api.polymarket.com/activity?user={ADDRESS}&limit={limit}&offset={offset}").json()
def is_market_closed(data):
    x = data[0]
    return not x.get("acceptingOrders")
def get_market_winner(slug):
    markets = get_market_info(slug)
    x = markets[0]

    if x.get("umaResolutionStatus") != "resolved":
        return None
    prices = json.loads(x.get("outcomePrices", "[]"))

    if len(prices) != 2:
        return None

    if prices[0] == "1":
        return "Up"
    elif prices[1] == "1":
        return "Down"
    
    return None
def init_polymarket_client():
    global POLYMARKET_CLIENT

    host="https://clob.polymarket.com"
    chain_id = 137 # Polygon mainnet
    public_key = PUBLIC_KEY
    private_key = PRIVATE_KEY
    funder = FUNDER_PUBLIC_KEY

    POLYMARKET_CLIENT = ClobClient(
        host=host,
        chain_id=chain_id,
        key=private_key,
        signature_type=0, 
        funder=funder
    )

    creds = POLYMARKET_CLIENT.create_or_derive_api_creds()
    POLYMARKET_CLIENT.set_api_creds(creds)
def create_polymarket_market_order(token_id, amount, side):
    order_args = MarketOrderArgs(
        token_id=token_id,
        amount=amount,
        side=side,
        order_type=OrderType.FAK
    )
    order = POLYMARKET_CLIENT.create_market_order(order_args)
    post = POLYMARKET_CLIENT.post_order(order, orderType=OrderType.FAK)
    return post
def create_polymarket_limit_order(token_id, amount, side, price):
    order_args = OrderArgs(
        token_id=token_id,
        size=amount,
        side=side,
        price=price
    )
    order = POLYMARKET_CLIENT.create_order(order_args)
    post = POLYMARKET_CLIENT.post_order(order, orderType=OrderType.GTC)
    return post
def allowance_info():
    params = BalanceAllowanceParams(asset_type=AssetType.COLLATERAL, signature_type=0)
    x = POLYMARKET_CLIENT.get_balance_allowance(params)
    allowances = x.get("allowances", {})
    print("Allowances:")
    for addr, value in allowances.items():
        print(f"* {addr} -> {value}")

    print("----")
def get_price(token_id):
    data = requests.get(f"https://clob.polymarket.com/midpoint?token_id={token_id}").json()
    if "mid" not in data:
        return None
    return float(data["mid"])
def get_token_id_from_side(data, side: int):
    market = data[0]
    if not data:
        return None

    tokens = json.loads(market["clobTokenIds"])
    return tokens[side]
def get_market_info_from_token_id(token_id):
    data = requests.get(f"https://gamma-api.polymarket.com/markets?clob_token_ids={token_id}").json()
    return data
def get_winning_token(token_id):
    data = get_market_info_from_token_id(token_id)
    print(data)
    market = data[0]
    token_ids = json.loads(market["clobTokenIds"])
    prices = json.loads(market["outcomePrices"])
    max_index = prices.index(max(prices, key=float))
    return token_ids[max_index]
def get_slug_from_token_id(token_id):
    data = get_market_info_from_token_id(token_id)
    if not data:
        return None

    market = data[0]
    return market["slug"]
def get_side_str_from_token_id(token_id):
    data = get_market_info_from_token_id(token_id)
    if not data:
        return None

    market = data[0]
    token_ids = json.loads(market["clobTokenIds"])
    outcomes = json.loads(market["outcomes"])
    index = token_ids.index(token_id)
    return outcomes[index]
def get_price_2(token_id, amount):
    try:
        price = POLYMARKET_CLIENT.calculate_market_price(token_id, "BUY", amount, OrderType.FOK)
        return price

    except PolyApiException as e:
        return None

    return price
def is_market_active(token_id):
    data = get_market_info_from_token_id(token_id)
    if not data:
        return None
    market = data[0]
    if market.get("closed") or market.get("archived"):
        return False
    if not market.get("acceptingOrders"):
        return False
    return True
def is_win(token_id):
    data = get_market_info_from_token_id(token_id)
    if not data:
        return None
    market = data[0]
    token_ids = json.loads(market["clobTokenIds"])
    prices = json.loads(market["outcomePrices"])
    
    if "1" not in prices and "1.0" not in prices:
        return None
    
    max_index = prices.index(max(prices, key=float))
    return token_ids[max_index] == token_id
def is_win_market(data, side_str):
    market = data[0]
    outcomes = json.loads(market["outcomes"])
    prices = json.loads(market["outcomePrices"])
    
    if "1" not in prices and "1.0" not in prices:
        return None
    
    max_index = prices.index(max(prices, key=float))
    return outcomes[max_index].lower() == side_str.lower()
def get_win_side_index(data):
    if not data:
        return None

    market = data[0]
    token_ids = json.loads(market["clobTokenIds"])
    prices = json.loads(market["outcomePrices"])
    
    if "1" not in prices and "1.0" not in prices:
        return None
    
    max_index = prices.index(max(prices, key=float))
    outcomes = json.loads(market["outcomes"])
    
    return outcomes[max_index]
def get_win_side_str_from_event_data(data):
    if not data:
        return None
    
    market = data[0]['markets'][0]
    prices = json.loads(market["outcomePrices"])
    outcomes = json.loads(market["outcomes"])
    
    prices_float = [float(p) for p in prices]
    
    if max(prices_float) < 0.99:
        return None
    
    max_index = prices_float.index(max(prices_float))
    return outcomes[max_index]
def cancel_all_limit_orders():
    return POLYMARKET_CLIENT.cancel_all()
def get_last_price(token_id):
    data = requests.get(f"https://clob.polymarket.com/last-trade-price?token_id={token_id}").json()
    price = data["price"]
    return float(price)
def get_condition_id(data):
    condition_id = data[0].get("conditionId", None)
    return condition_id
def get_condition_id_from_event(data):
    return data[0]["markets"][0]["conditionId"]
def get_slug_from_data(data):
    if not data:
        return None

    market = data[0]
    return market["slug"]
def get_title_from_data(data):
    if not data:
        return ""
    return data[0].get("question", "")
def get_side_str_from_data(data, token_id):
    if not data:
        return None

    market = data[0]
    token_ids = json.loads(market["clobTokenIds"])
    outcomes = json.loads(market["outcomes"])
    index = token_ids.index(token_id)
    return outcomes[index]
def is_market_active_from_data(data):
    if not data:
        return None

    market = data[0]
    if market.get("closed") or market.get("archived"):
        return False
    if not market.get("acceptingOrders"):
        return False
    return True
def get_token_id_from_side_str(data, side_str):
    market = data[0]
    if not data:
        return None
    tokens = json.loads(market["clobTokenIds"])
    outcomes = json.loads(market["outcomes"])
    side_index = [o.lower() for o in outcomes].index(side_str.lower())
    return tokens[side_index]
def get_available_liquidity(token_id: str, side: str):
    try:
        order_book = POLYMARKET_CLIENT.get_order_book(token_id)
        if side == "Buy":
            if not order_book.asks:
                return 0.0
            best = min(order_book.asks, key=lambda x: float(x.price))
        else:
            if not order_book.bids:
                return 0.0
            best = max(order_book.bids, key=lambda x: float(x.price))
        return float(best.size)
    except Exception:
        return 0.0
def ping_clob():
    start = time.time()
    requests.get("https://clob.polymarket.com/")
    end = time.time()
    print(f"Ping: {(end - start) * 1000:.2f}ms")
def get_activity_by_condition_id(condition_id: str):
    url = f"https://data-api.polymarket.com/activity?user={WALLETS_TO_COPY}&market={condition_id}&type=TRADE"
    response = requests.get(url)
    return response.json()
def get_all_sells(limit):
    url = f"https://data-api.polymarket.com/activity?user={WALLETS_TO_COPY}&type=TRADE&side=SELL&limit={limit}"
    response = requests.get(url)
    data = response.json()
    return data
def get_active_orders():
    return requests.get(f"https://data-api.polymarket.com/positions?user={PUBLIC_KEY}").json()
def merge_and_sort(active, closed):
    combined = active + closed
    combined.sort(key=lambda x: x["slug"], reverse=True)
    return combined


def print_backtest_results_by_wallet_score_v2(backtest_data):
    MIN_TRADES = 20
    MIN_WINRATE = 55
    MIN_PROFIT_FACTOR = 2.0
    MIN_PROFIT_USDC = 50
    MIN_WALLET_SCORE = 7.0
    MIN_STABILITY = 25
    MAX_AVG_BUY_PRICE = 60

    filtered = []

    for backtest in backtest_data:
        if backtest.get("trades", 0) < MIN_TRADES:
            continue
        if backtest.get("winrate_pct", 0) < MIN_WINRATE:
            continue
        pf = backtest.get("profit_factor", 0)
        if pf == float("inf") or pf < MIN_PROFIT_FACTOR:
            continue
        if backtest.get("profit_usdc", 0) < MIN_PROFIT_USDC:
            continue
        if backtest.get("wallet_score", 0) < MIN_WALLET_SCORE:
            continue
        if backtest.get("stability_pct", 0) < MIN_STABILITY:
            continue
        if backtest.get("avg_buy_price_pct", 100) > MAX_AVG_BUY_PRICE:
            continue

        filtered.append(backtest)

    def composite_score(b):
        ws  = b.get("wallet_score", 0) * 2
        wr  = b.get("winrate_pct", 0) / 10
        pf  = min(b.get("profit_factor", 0), 10)
        st  = b.get("stability_pct", 0) / 10
        pr  = min(b.get("profit_usdc", 0) / 500, 5)
        abp = (100 - b.get("avg_buy_price_pct", 100)) / 20  # lower buy price = bonus
        return ws + wr + pf + st + pr + abp

    filtered.sort(key=composite_score, reverse=True)

    print(f"\n{'='*80}")
    print(f"{'WALLET SCORE v2 — TOP COPY TRADE CANDIDATES':^80}")
    print(f"{'='*80}")
    print(f"  trades ≥ {MIN_TRADES} | winrate ≥ {MIN_WINRATE}% | PF ≥ {MIN_PROFIT_FACTOR} | profit ≥ {MIN_PROFIT_USDC} | stability ≥ {MIN_STABILITY}% | avgBuy ≤ {MAX_AVG_BUY_PRICE}%")
    print(f"  Found: {len(filtered)} wallets\n")

    if not filtered:
        # fallback — ukaž top 5 bez filtrov, len zoradené
        print("  [!] No wallets passed filters. Showing top 5 by composite score:\n")
        candidates = [b for b in backtest_data if b.get("profit_usdc", 0) > 0 and b.get("profit_factor", 0) != float("inf")]
        candidates.sort(key=composite_score, reverse=True)
        filtered = candidates[:5]

    for i, b in enumerate(filtered, 1):
        cs  = round(composite_score(b), 2)
        pf  = b.get("profit_factor", 0)
        pf_str = f"{pf:.2f}" if pf != float("inf") else "∞"

        print(f"  #{i:<3} WalletScore: {b['wallet_score']}/10  |  Composite: {cs}")
        print(f"       {b['address']}")
        print(f"       Profit: {b['profit_usdc']} USDC  |  Winrate: {b['winrate_pct']}%  |  PF: {pf_str}")
        print(f"       Trades: {b['trades']}  |  Stability: {b['stability_pct']}%  |  AvgBuyPrice: {b.get('avg_buy_price_pct', '?')}%")
        print(f"       Wins: {b['total_wins']}  |  Losses: {b['total_losses']}  |  MaxDD: {b['max_drawdown_pct']}%")
        # print(f"       Period: {b['from']} → {b['to']}")
        print("")
def print_backtest_results_by_min_avg_buy_price(backtest_data):
    for backtest in sorted(backtest_data, key=lambda x: x.get("avg_buy_price_pct", float("inf"))):
        score = backtest.get("avg_buy_price_pct", None)
        
        if score is None:
            continue

        if score <= 10:
            tier = "10/9"
        elif score <= 20:
            tier = "9/8"
        elif score <= 30:
            tier = "8/7"
        elif score <= 40:
            tier = "7/6"
        elif score <= 50:
            tier = "6/5"
        elif score <= 60:
            tier = "5/4"
        elif score <= 70:
            tier = "4/3"
        elif score <= 80:
            tier = "3/2"
        elif score <= 90:
            tier = "2/1"
        else:
            tier = "1/0"

        if SKIP_NOT_PROFIT_WALLETS:
            if backtest.get("profit_usdc", 0) <= 0:
                continue

        print(f"[{tier}] AvgBuyPrice: {score}% | {backtest['address']} | Profit: {backtest['profit_usdc']} USDC | Winrate: {backtest['winrate_pct']}%")
def get_leaderboard(category: str, time_period: str, order_by: str, limit: int):
    url = "https://data-api.polymarket.com/v1/leaderboard"
    page_size = 50 # max per request
    results = []
    offset = 0

    while len(results) < limit:
        fetch = min(page_size, limit - len(results))
        params = {
            "category": category,
            "timePeriod": time_period,
            "orderBy": order_by,
            "limit": fetch,
            "offset": offset,
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        page = response.json()

        if not page:
            break

        results.extend(page)
        offset += len(page)

        if len(page) < fetch:
            break

    return results
def print_backtest_results_by_stability(backtest_data):
    for backtest in sorted(backtest_data, key=lambda x: x.get("stability_pct", 0), reverse=True):
        score = backtest.get("stability_pct", 0)
        
        if score >= 90:
            tier = "10/9"
        elif score >= 80:
            tier = "9/8"
        elif score >= 70:
            tier = "8/7"
        elif score >= 60:
            tier = "7/6"
        elif score >= 50:
            tier = "6/5"
        elif score >= 40:
            tier = "5/4"
        elif score >= 30:
            tier = "4/3"
        elif score >= 20:
            tier = "3/2"
        elif score >= 10:
            tier = "2/1"
        else:
            tier = "1/0"
        
        if SKIP_NOT_PROFIT_WALLETS:
            if backtest.get("profit_usdc", 0) <= 0:
                continue

        print(f"[{tier}] Stability: {score}% | {backtest['address']} | Profit: {backtest['profit_usdc']} USDC | Winrate: {backtest['winrate_pct']}%")
def print_backtest_results_by_profit_factor(backtest_data):
    for backtest in sorted(backtest_data, key=lambda x: x.get("profit_factor", 0) if x.get("profit_factor") != float("inf") else 0, reverse=True):
        score = backtest.get("profit_factor", 0)
        
        if score == float("inf"):
            continue
        elif score >= 10:
            tier = "10/9"
        elif score >= 5:
            tier = "9/8"
        elif score >= 3:
            tier = "8/7"
        elif score >= 2:
            tier = "7/6"
        elif score >= 1.5:
            tier = "6/5"
        else:
            continue
        
        if SKIP_NOT_PROFIT_WALLETS:
            if backtest.get("profit_usdc", 0) <= 0:
                continue

        print(f"[{tier}] ProfitFactor: {score} | {backtest['address']} | Profit: {backtest['profit_usdc']} USDC | Winrate: {backtest['winrate_pct']}%")
def print_backtest_results_by_winrate(backtest_data):
    for backtest in sorted(backtest_data, key=lambda x: x.get("winrate_pct", 0), reverse=True):
        score = backtest.get("winrate_pct", 0)
        
        if score >= 75:
            tier = "10/9"
        elif score >= 65:
            tier = "9/8"
        elif score >= 60:
            tier = "8/7"
        elif score >= 55:
            tier = "7/6"
        elif score >= 50:
            tier = "6/5"
        else:
            continue
        
        if SKIP_NOT_PROFIT_WALLETS:
            if backtest.get("profit_usdc", 0) <= 0:
                continue

        print(f"[{tier}] Winrate: {score}% | {backtest['address']} | Profit: {backtest['profit_usdc']} USDC | ProfitFactor: {backtest['profit_factor']}")
def print_backtest_results_by_wallet_score(backtest_data):
    backtest_data.sort(key=lambda x: x.get("wallet_score", 0), reverse=True)
    
    for backtest in backtest_data:
        score = backtest.get("wallet_score", 0)
        
        if score >= 9:
            tier = "10/9"
        elif score >= 8:
            tier = "9/8"
        elif score >= 7:
            tier = "8/7"
        elif score >= 6:
            tier = "7/6"
        elif score >= 5:
            tier = "6/5"
        else:
            continue
        
        if SKIP_NOT_PROFIT_WALLETS:
            if backtest.get("profit_usdc", 0) <= 0:
                continue

        print(f"[{tier}] Score: {score}/10 | {backtest['address']} | Profit: {backtest['profit_usdc']} USDC | Winrate: {backtest['winrate_pct']}%")
def find_good_address():
    global WALLETS_TO_COPY
    leaderboard = get_leaderboard(LEADBOARD_CATEGORY, LEADBOARD_TIME_PERIOD, "PNL", LEADBOARD_LIMIT)
    
    backtest_data = []
    index = 0

    for trader in leaderboard:
        print(f"{index} of {LEADBOARD_LIMIT}")
        WALLETS_TO_COPY = trader["proxyWallet"]
        if not is_account_active(5):
            print(f"* Account is not active, skipping... {WALLETS_TO_COPY}")
            index += 1
            continue
        backtest = run_backtest_from_url(False, False, False, True)
        backtest_data.append(backtest)
        index += 1

    print("")
    print("Filter by wallet score:")
    print_backtest_results_by_wallet_score(backtest_data)
    print("")
    print("Filter by stability:")
    print_backtest_results_by_stability(backtest_data)
    print("")
    print("Filter by profit factor:")
    print_backtest_results_by_profit_factor(backtest_data)
    print("")
    print("Filter by winrate:")
    print_backtest_results_by_winrate(backtest_data)
    print("")
    print("Filter by min avg buy price:")
    print_backtest_results_by_min_avg_buy_price(backtest_data)
    print("")
    print("Filter by wallet score v2:")
    print_backtest_results_by_wallet_score_v2(backtest_data)



        
def get_active_orders_trader(limit, offset):
    return requests.get(f"https://data-api.polymarket.com/positions?user={WALLETS_TO_COPY}&limit={limit}&offset={offset}").json()
def get_active_orders_trader_2(limit):
    all_data = []
    offset = 0
    batch_size = 50

    while len(all_data) < limit:
        data = get_active_orders_trader(batch_size, offset)

        if not data:
            break

        all_data.extend(data)

        if len(data) < batch_size:
            break

        offset += batch_size

    return all_data[:limit]

def calc_scaled_invested(trader_invested: float, trader_min: float, trader_max: float, my_min: float, my_max: float):
    if trader_max == trader_min:
        return my_min
    ratio = (trader_invested - trader_min) / (trader_max - trader_min)
    scaled = my_min + ratio * (my_max - my_min)
    return round(max(my_min, min(my_max, scaled)), 2)
def count_same_token_ids(trades: list, token_id: str):
    return [t.token_id for t in trades].count(token_id)
def count_same_token_ids_2(token_ids: list, asset: str):
    return token_ids.count(asset)
def count_same_slugs_2(slugs: list, slug: str):
    return slugs.count(slug)
def avg_duplicate_token_ids(token_ids: list):
    if not token_ids:
        return 0.0
    
    counts = {}
    for token_id in token_ids:
        counts[token_id] = counts.get(token_id, 0) + 1
    
    return sum(counts.values()) / len(counts)
def count_same_slugs(trades: list, slug: str):
    return [t.slug for t in trades].count(slug)


# BACKTEST CODE
def print_stats_by_hour(by_hour: dict):
    for hour, stats in sorted(by_hour.items(), key=lambda x: int(x[0])):
        print(f"{stats['hour']} / size: {stats['size']} / winrate: {stats['winrate']}% / stability: {stats['stability']} / pf: {stats['profit_factor']}")
def get_hour_from_slug(slug: str):
    import re
    from datetime import datetime, timezone
    match = re.search(r'-(\d{10})$', slug)
    if not match:
        return None
    ts = int(match.group(1))
    return datetime.fromtimestamp(ts, timezone.utc).hour
def calc_stats_by_hour(data: list):    
    hours = defaultdict(list)
    
    for entry in data:
        slug = entry.get("slug", "")
        match = re.search(r'-(\d{10})$', slug)
        if not match:
            continue
        ts = int(match.group(1))
        hour = datetime.fromtimestamp(ts, timezone.utc).hour
        hours[hour].append(entry)
    
    result = {}
    
    for hour, entries in sorted(hours.items()):
        result[hour] = {
            "hour": f"{hour:02d}:00-{hour:02d}:59",
            "size": len(entries),
            "winrate": round(
                sum(1 for e in entries if e["realizedPnl"] > 0) / len(entries) * 100, 2
            ),
            "stability": calc_stability(entries),
            "profit_factor": calc_profit_factor(entries),
        }
    
    return result
def calc_avg_pnl(pnls):
    if not pnls:
        return 0
    return round(sum(pnls) / len(pnls), 2)
def adjust_pnl(pnl, worsening_pct):
    factor = worsening_pct / 100
    if pnl > 0:
        return pnl * (1 - factor)
    else:
        return pnl * (1 + factor)
def calc_trader_min_max(data: list):
    if not data:
        return 0, 0

    investments = [e["avgPrice"] * e["totalBought"] for e in data]
    return round(min(investments), 2), round(max(investments), 2)
def calc_wallet_score(winrate: float, profit_factor: float, max_dd_pct: float, stability: float, avg_price_pct: float):
    # winrate score 0-10 (50% = 5, 60% = 10)
    winrate_score = min((winrate - 40) / 20 * 10, 10)
    winrate_score = max(winrate_score, 0)

    # profit factor score 0-10 (1.0 = 0, 2.0 = 10)
    pf_score = min((profit_factor - 1.0) / 1.0 * 10, 10)
    pf_score = max(pf_score, 0)

    # max drawdown score 0-10 (0% = 10, 50%+ = 0)
    dd_score = max(10 - (max_dd_pct / 5), 0)

    # stability score 0-10
    stability_score = stability / 10

    # avg price score 0-10 (30% = 10, 70%+ = 0)
    avg_price_score = max(10 - ((avg_price_pct - 30) / 40 * 10), 0)
    avg_price_score = min(avg_price_score, 10)

    # weighted average
    score = (
        winrate_score     * 0.25 +
        pf_score          * 0.30 +
        dd_score          * 0.20 +
        stability_score   * 0.15 +
        avg_price_score   * 0.10
    )

    return round(score, 2)
def calc_profit_factor(data: list):
    gross_win = sum(e["realizedPnl"] for e in data if e["realizedPnl"] > 0)
    gross_loss = sum(abs(e["realizedPnl"]) for e in data if e["realizedPnl"] < 0)
    if gross_loss == 0:
        return float("inf")
    return round(gross_win / gross_loss, 2)
def calc_max_drawdown(data: list):
    balance = BACKTEST_BALANCE
    peak = balance
    max_dd = 0
    max_dd_pct = 0

    for entry in data:
        realized = entry.get("realizedPnl", 0)
        balance += realized

        if balance > peak:
            peak = balance

        drawdown = peak - balance
        drawdown_pct = (drawdown / peak) * 100 if peak > 0 else 0

        if drawdown > max_dd:
            max_dd = drawdown
            max_dd_pct = drawdown_pct

    return round(max_dd, 2), round(max_dd_pct, 2)
def plot_backtest_pnl(data, auto_open):
    backtest_balance = BACKTEST_BALANCE

    if not data:
        print("No data to plot.")
        return

    trader_min, trader_max = calc_trader_min_max(data)

    # ── collect per-trade results ──────────────────────────────────────────
    trades = []
    cumulative = backtest_balance
    cum_values = [backtest_balance]

    coin_pnl = {"btc": [], "eth": [], "sol": [], "xrp": [], "doge": [], "other": []}

    for i, entry in enumerate(data):
        slug       = entry.get("slug", "")
        title      = entry.get("title", f"Trade {i}")
        realized   = entry.get("realizedPnl", 0)
        pnl = realized

        skip = entry.get("skip", None)
        if skip is None:
            continue
        if skip:
            continue

        cumulative += pnl
        cum_values.append(cumulative)

        coin = "other"
        for c in ("btc", "eth", "sol", "xrp", "doge"):
            if c in slug.lower():
                coin = c
                break

        trades.append({
            "index": i,
            "title": title[:40],
            "pnl":   pnl,
            "coin":  coin,
        })
        coin_pnl[coin].append(pnl)

        if cumulative <= 0:
            break   # account burned

    # ── setup ─────────────────────────────────────────────────────────────
    fig, axes = plt.subplots(3, 1, figsize=(14, 14))
    fig.suptitle("Backtest — Realized PnL Analysis", fontsize=15, fontweight="bold", y=0.98, color="white")
    fig.patch.set_facecolor("#0f1117")
    for ax in axes:
        ax.set_facecolor("#161b22")
        ax.tick_params(colors="#c9d1d9")
        ax.xaxis.label.set_color("#c9d1d9")
        ax.yaxis.label.set_color("#c9d1d9")
        ax.title.set_color("#e6edf3")
        for spine in ax.spines.values():
            spine.set_edgecolor("#30363d")

    GREEN = "#3fb950"
    RED   = "#f85149"
    BLUE  = "#58a6ff"

    x = list(range(len(trades)))

    # ── 1. Cumulative balance curve ────────────────────────────────────────
    ax1 = axes[0]
    ax1.plot(range(len(cum_values)), cum_values, color=BLUE, linewidth=1.8, zorder=3)
    ax1.fill_between(range(len(cum_values)), cum_values, backtest_balance,
                     where=[v >= backtest_balance for v in cum_values],
                     color=GREEN, alpha=0.18)
    ax1.fill_between(range(len(cum_values)), cum_values, backtest_balance,
                     where=[v < backtest_balance for v in cum_values],
                     color=RED, alpha=0.18)
    ax1.axhline(backtest_balance, color="#8b949e", linewidth=0.8, linestyle="--", label="Start balance")
    ax1.set_title("Cumulative balance")
    ax1.set_xlabel("Trade #")
    ax1.set_ylabel("USDC")
    ax1.legend(facecolor="#161b22", edgecolor="#30363d", labelcolor="#c9d1d9")
    ax1.grid(axis="y", color="#21262d", linewidth=0.6)

    # ── 2. Per-trade PnL bars ──────────────────────────────────────────────
    ax2 = axes[1]
    bar_colors = [GREEN if t["pnl"] >= 0 else RED for t in trades]
    ax2.bar(x, [t["pnl"] for t in trades], color=bar_colors, width=0.7, zorder=3)
    ax2.axhline(0, color="#8b949e", linewidth=0.8)
    ax2.set_title("Per-trade realized PnL")
    ax2.set_xlabel("Trade #")
    ax2.set_ylabel("PnL (USDC)")
    ax2.grid(axis="y", color="#21262d", linewidth=0.6)

    total_pnl = sum(t["pnl"] for t in trades)
    win_count  = sum(1 for t in trades if t["pnl"] > 0)
    loss_count = len(trades) - win_count
    ax2.set_title(
        f"Per-trade realized PnL  |  "
        f"Trades: {len(trades)}  W: {win_count}  L: {loss_count}  "
        f"Winrate: {win_count/len(trades)*100:.1f}%  "
        f"Net: {total_pnl:+.2f} USDC"
    )

    # ── 3. Per-coin PnL breakdown ──────────────────────────────────────────
    ax3 = axes[2]
    COIN_COLORS = {
        "btc":   "#f7931a",
        "eth":   "#627eea",
        "sol":   "#9945ff",
        "xrp":   "#00aae4",
        "doge":  "#c2a633",
        "other": "#8b949e",
    }
    coins   = [c for c in COIN_COLORS if coin_pnl[c]]
    totals  = [sum(coin_pnl[c]) for c in coins]
    colors  = [COIN_COLORS[c] for c in coins]
    bars    = ax3.bar(coins, totals, color=colors, width=0.5, zorder=3)

    for bar, val in zip(bars, totals):
        ax3.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + (max(abs(v) for v in totals) * 0.02),
            f"{val:+.2f}",
            ha="center", va="bottom", fontsize=10, color="#e6edf3"
        )

    ax3.axhline(0, color="#8b949e", linewidth=0.8)
    ax3.set_title("Net PnL by coin")
    ax3.set_ylabel("PnL (USDC)")
    ax3.set_xticks(range(len(coins)))
    ax3.set_xticklabels([c.upper() for c in coins])
    ax3.grid(axis="y", color="#21262d", linewidth=0.6)

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.savefig("backtest_pnl.png", dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    if auto_open:
        plt.show()
    # print("Plot saved to backtest_pnl.png")
def calc_avg_price_pct(data: list):
    if not data:
        return 0.0

    prices = [entry["avgPrice"] * 100 for entry in data]
    return round(sum(prices) / len(prices), 2)
def calc_stability(data: list):
    wins = []
    losses = []
    
    for entry in data:
        invested = entry["avgPrice"] * entry["totalBought"]
        pnl = entry["realizedPnl"]
        
        if pnl > 0:
            wins.append(pnl)
        else:
            losses.append(abs(invested))
    
    if not wins or not losses:
        return 0.0
    
    avg_win = sum(wins) / len(wins)
    avg_loss = sum(losses) / len(losses)
    winrate = len(wins) / (len(wins) + len(losses))
    
    # expected value per trade
    ev = (winrate * avg_win) - ((1 - winrate) * avg_loss)
    ev_max = max(avg_win, avg_loss)
    
    # normalize to 0-100
    stability = max(0.0, min((ev / ev_max + 1) / 2 * 100, 100.0))
    
    return round(stability, 2)
def get_trade_by_slug(slug: str):
    for trade in DATA:
        if trade["slug"] == slug:
            return trade
    return None
def sort_trades_by_time(data):
    def extract_timestamp(entry):
        slug = entry.get("slug", "")
        parts = slug.rsplit("-", 1)
        try:
            return int(parts[-1])
        except ValueError:
            return 0
    
    return sorted(data, key=extract_timestamp)
def run_backtest_from_url(print_all_trades, print_data, gen_plot, get_data):
    print("Backtesting...")
    global WALLETS_TO_COPY



    profit = BACKTEST_BALANCE
    win = 0
    loss = 0



    btc_win = 0
    btc_loss = 0
    eth_win = 0
    eth_loss = 0
    sol_win = 0
    sol_loss = 0
    xrp_win = 0
    xrp_loss = 0
    doge_win = 0
    doge_loss = 0

    btc_profit = 0
    eth_profit = 0
    sol_profit = 0
    xrp_profit = 0
    doge_profit = 0



    # deposit = get_total_deposited(WALLETS_TO_COPY)
    deposit = 0
    index = 0



    if FILTER_TRADES_BY_YOUR_TRADES:
        # my data
        backup = WALLETS_TO_COPY # change address for get_closed_trades2, get_active_orders_trader_2
        WALLETS_TO_COPY = PUBLIC_KEY
        data = get_closed_trades2(BACKTEST_LIMIT) # load data from closed trades
        active_data = get_active_orders_trader_2(BACKTEST_LIMIT) # load data from active trades (closed but not redeemed)
        data = merge_and_sort(active_data, data)
        s = data[:BACKTEST_LIMIT] # crop data
        WALLETS_TO_COPY = backup



    # leader data
    data = get_closed_trades2(BACKTEST_LIMIT) # load data from closed trades
    active_data = get_active_orders_trader_2(BACKTEST_LIMIT) # load data from active trades (closed but not redeemed)
    data = merge_and_sort(active_data, data)
    data = data[:BACKTEST_LIMIT] # crop data



    # only same trades
    if FILTER_TRADES_BY_YOUR_TRADES:
        my_slugs = set(d['slug'] for d in s)
        data = [d for d in data if d['slug'] in my_slugs]



    data = sort_trades_by_time(data)
    # condition_id = data[0].get("conditionId", None)

    token_ids = []
    avg_token_ids = []
    slugs = []
    win_avg_pnls = []
    loss_avg_pnls = []
    by_hour = calc_stats_by_hour(data)
    # print("Data over time.")
    if print_all_trades:
        print_stats_by_hour(by_hour)

    for entry in data[:]: # copy
        condition_id = entry["conditionId"]
        slug = entry["slug"]
        title = entry["title"]
        outcome_index = entry["outcomeIndex"]
        asset = entry["asset"] # asset is token id
        avg_token_ids.append(asset)
        entry["skip"] = False



        if False:
            result = any(t.slug == slug for t in trades) # just trades from file
            if result:
                continue



        same_token_id = count_same_token_ids_2(token_ids, asset)
        if same_token_id >= MAX_DUPLICATE_POSITIONS:
            data.remove(entry)
            continue
        token_ids.append(asset)

        same_slug = count_same_slugs_2(slugs, slug)
        if same_slug >= MAX_DUPLICATE_POSITIONS_SLUG:
            data.remove(entry)
            continue
        slugs.append(slug)



        if ALLOWED_HOURS:
            hour = get_hour_from_slug(slug)
            if hour not in ALLOWED_HOURS:
                data.remove(entry)
                continue



        # turn off
        if contains_word(slug, "btc"):
            if not ENABLE_BTC:
                data.remove(entry)
                continue
        if contains_word(slug, "eth"):
            if not ENABLE_ETH:
                data.remove(entry)
                continue
        if contains_word(slug, "sol"):
            if not ENABLE_SOL:
                data.remove(entry)
                continue
        if contains_word(slug, "xrp"):
            if not ENABLE_XRP:
                data.remove(entry)
                continue
        if contains_word(slug, "doge"):
            if not ENABLE_DOGE:
                data.remove(entry)
                continue
        # if not ENABLE_OTHER_MARKETS:
            # if not contains_word(slug, "btc eth sol xrp doge"):
                # entry["skip"] = True
                # continue
        if FILTER_TRADES_BY_TITLE:
            if not contains_word(title, FILTER_TRADES_BY_TITLE):
                data.remove(entry)
                continue



        total_bought = entry["totalBought"]
        realized_pnl = entry["realizedPnl"] # do not edit

        if USE_WORSE_PNL != 0:
            realized_pnl = adjust_pnl(realized_pnl, USE_WORSE_PNL) # 35
            entry["realizedPnl"] = realized_pnl

        cur_price = entry["curPrice"]
        outcome = entry["outcome"]
        avgPrice = entry["avgPrice"]

        if USE_WORSE_ENTRY != 0:
            adjusted_price = adjust_price(avgPrice, USE_WORSE_ENTRY)
            avgPrice = adjusted_price

        invested = avgPrice * entry["totalBought"]
        original_invested = entry["avgPrice"] * entry["totalBought"] # do not modify
        trader_invested = invested # do not modify
        my_invest = 0
        outcome = entry["outcome"]



        if original_invested < MIN_TRADER_AMOUNT:
            data.remove(entry)
            continue



        if MODE == "FIXED":
            my_invest = FIXED
        elif MODE == "AUTO":
            my_invest = calc_scaled_invested(original_invested, TRADER_MIN, TRADER_MAX, MIN, MAX)
        else:
            break

        if USE_YOUR_AMOUNT_BACKTEST:
            invested = my_invest
            realized_pnl = get_scaled_pnl(entry, avgPrice, my_invest)



        if realized_pnl > 0:
            # profit += invested
            profit += realized_pnl
            win += 1
            if print_all_trades:
                print(f"{index}: + Win: Invested: {(invested):.2f} USDC, P&L: {realized_pnl:.2f} USDC, Return: {invested + realized_pnl:.2f} USDC, Slug: {slug}, Title: {title}, Trader invested: {trader_invested:.2f}, My invest: {my_invest:.2f}, Outcome: {outcome}, Price: {avgPrice:.2f}")

            win_avg_pnls.append(realized_pnl)
            if contains_word(slug, "btc"):
                btc_win += 1
                btc_profit += realized_pnl
            elif contains_word(slug, "eth"):
                eth_win += 1
                eth_profit += realized_pnl
            elif contains_word(slug, "sol"):
                sol_win += 1
                sol_profit += realized_pnl
            elif contains_word(slug, "xrp"):
                xrp_win += 1
                xrp_profit += realized_pnl
            elif contains_word(slug, "doge"):
                doge_win += 1
                doge_profit += realized_pnl
        else:
            if BLOCK_SELL_POSITIONS: # so wait to end of market, wrong side = 100% loss
                realized_pnl = -invested

            profit += realized_pnl
            loss += 1
            if print_all_trades:
                print(f"{index}: - Loss: Invested: {(invested):.2f} USDC, P&L: {realized_pnl:.2f} USDC, Return: {invested + realized_pnl:.2f} USDC, Slug: {slug}, Title: {title}, Trader invested: {trader_invested:.2f}, My invest: {my_invest:.2f}, Outcome: {outcome}, Price: {avgPrice:.2f}")

            loss_avg_pnls.append(realized_pnl)
            if contains_word(slug, "btc"):
                btc_loss += 1
                btc_profit += realized_pnl
            elif contains_word(slug, "eth"):
                eth_loss += 1
                eth_profit += realized_pnl
            elif contains_word(slug, "sol"):
                sol_loss += 1
                sol_profit += realized_pnl
            elif contains_word(slug, "xrp"):
                xrp_loss += 1
                xrp_profit += realized_pnl
            elif contains_word(slug, "doge"):
                doge_loss += 1
                doge_profit += realized_pnl

        index += 1

        # fast flag
        if True:
            if profit < 0:
                print("------------")
                print("!!! Burned account. !!!")
                print("------------")
                break



        # for plot
        entry["realizedPnl"] = realized_pnl # ????


    # data
    stability = calc_stability(data)
    avg_price_pct = calc_avg_price_pct(data)
    max_dd, max_dd_pct = calc_max_drawdown(data)
    all_sells = get_all_sells(1000)
    sells_len = len(all_sells) # wallet use also sells?
    profit_factor = calc_profit_factor(data)
    trader_min, trader_max = calc_trader_min_max(data)
    win_avg = calc_avg_pnl(win_avg_pnls)
    loss_avg = calc_avg_pnl(loss_avg_pnls)

    if not data:
        return 

    print("----")
    print(f"* Address to backtest: {WALLETS_TO_COPY}")
    print(f"* Your address: {PUBLIC_KEY}")
    print(f"* Trades: {len(data)}")
    print(f"* Deposited: {deposit:.2f} USDC")
    print(f"* Stability: {stability}%")
    print(f"* Average buy price: {avg_price_pct}% <---")
    print(f"* Max drawdown: {max_dd:.2f} USDC ({max_dd_pct:.2f}%)")
    print(f"* Sells count (of 1000): {sells_len}")
    print(f"* Profit factor: {profit_factor} <---")
    print(f"* Trader min/max investment: {trader_min:.2f}/{trader_max:.2f} USDC")
    print(f"* Average duplicate orders: {avg_duplicate_token_ids(avg_token_ids):.2f}")
    print(f"* Avg win/loss pnl: {win_avg}/{loss_avg}")
    print(f"* From: {data[0]["title"]}")
    print(f"* To: {data[-1]["title"]}")
    print(f"* Total wins: {win}")
    print(f"* Total losses: {loss}")
    print(f"* Balance: {profit:.2f} USDC (From {BACKTEST_BALANCE} USDC)")
    print(f"* Profit: {profit - BACKTEST_BALANCE:.2f} USDC")
    total = win + loss
    winrate = (win / total) * 100 if total > 0 else 0
    print(f"* Winrate: {winrate:.2f}%")

    wallet_score = calc_wallet_score(winrate, profit_factor, max_dd_pct, stability, avg_price_pct)
    print(f"* Wallet score: {wallet_score}/10 <---")

    print("----")

    if get_data:
        results = {
            "address": WALLETS_TO_COPY,
            "your_address": PUBLIC_KEY,
            "trades": len(data),
            "deposited_usdc": round(deposit, 2),
            "stability_pct": stability,
            "avg_buy_price_pct": avg_price_pct,
            "max_drawdown_usdc": round(max_dd, 2),
            "max_drawdown_pct": round(max_dd_pct, 2),
            "sells_count": sells_len,
            "profit_factor": profit_factor,
            "trader_min_usdc": round(trader_min, 2),
            "trader_max_usdc": round(trader_max, 2),
            "avg_duplicate_orders": avg_duplicate_token_ids(avg_token_ids),
            "avg_win_pnl": win_avg,
            "avg_loss_pnl": loss_avg,
            "from": data[0]["title"],
            "to": data[-1]["title"],
            "total_wins": win,
            "total_losses": loss,
            "balance_usdc": round(profit, 2),
            "initial_balance_usdc": BACKTEST_BALANCE,
            "profit_usdc": round(profit - BACKTEST_BALANCE, 2),
            "winrate_pct": round(winrate, 2),
            "wallet_score": wallet_score,
        }

        return results

    if print_data:
        print(f"* BTC win: {btc_win} loss: {btc_loss}")
        total = btc_win + btc_loss
        win_rate = (btc_win / total * 100) if total > 0 else 0
        print(f"* Winrate: {win_rate:.2f}%")
        print(f"* ETH win: {eth_win} loss: {eth_loss}")
        total = eth_win + eth_loss
        win_rate = (eth_win / total * 100) if total > 0 else 0
        print(f"* Winrate: {win_rate:.2f}%")
        print(f"* SOL win: {sol_win} loss: {sol_loss}")
        total = sol_win + sol_loss
        win_rate = (sol_win / total * 100) if total > 0 else 0
        print(f"* Winrate: {win_rate:.2f}%")
        print(f"* XRP win: {xrp_win} loss: {xrp_loss}")
        total = xrp_win + xrp_loss
        win_rate = (xrp_win / total * 100) if total > 0 else 0
        print(f"* Winrate: {win_rate:.2f}%")
        print(f"* DOGE win: {doge_win} loss: {doge_loss}")
        total = doge_win + doge_loss
        win_rate = (doge_win / total * 100) if total > 0 else 0
        print(f"* Winrate: {win_rate:.2f}%")

        print("----")

        print(f"* BTC profit: {btc_profit:.2f} USDC")
        print(f"* ETH profit: {eth_profit:.2f} USDC")
        print(f"* SOL profit: {sol_profit:.2f} USDC")
        print(f"* XRP profit: {xrp_profit:.2f} USDC")
        print(f"* DOGE profit: {doge_profit:.2f} USDC")

        print("----")


    if gen_plot:
        total = win + loss
        if total != 0:
            print("* Creating plot, please wait...")
            plot_backtest_pnl(data, False)

# websocket
async def subscribe(ws):
    ORDER_FILLED_TOPIC = "0xd0a08e8c493f9c94f29311604c9de1b4e8c8d4c06bd0c789af57f2d65bfec0f6"
    
    await ws.send(json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_subscribe",
        "params": ["logs", {
            "address": [
                "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E",
                "0xC5d563A36AE78145C45a50134d48A1215220f80a"
            ],
            "topics": [ORDER_FILLED_TOPIC]
        }]
    }))
    print("Running...")
    print("----")
async def listen_old(ws):
    wallets = {w.lower() for w in WALLETS_TO_COPY_2}
    
    async for raw in ws:
        data = json.loads(raw)
        if data is None:
            print("Data is empty.")
            continue
        if "params" not in data:
            continue
        log = data["params"]["result"]
        if len(log.get("topics", [])) < 4:
            continue
        
        maker = "0x" + log["topics"][2][-40:]
        # taker is the exchange relayer, NOT a user wallet — ignore it for filtering
        if maker.lower() not in wallets:
            continue
        
        asyncio.create_task(handle_transfer(log))

async def listen(ws):
    wallets = {w.lower() for w in WALLETS_TO_COPY_2}
    
    async for raw in ws:
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            print(f"json is not valid.")
            continue
        
        if "params" not in data:
            continue
        log = data["params"]["result"]
        if len(log.get("topics", [])) < 4:
            continue
        
        maker = "0x" + log["topics"][2][-40:]
        if maker.lower() not in wallets:
            continue
        
        asyncio.create_task(handle_transfer(log))
async def handle_transfer(log):
    ORDER_FILLED_ABI = {
        "name": "OrderFilled",
        "type": "event",
        "anonymous": False,
        "inputs": [
            {"name": "orderHash",    "type": "bytes32", "indexed": True},
            {"name": "maker",        "type": "address", "indexed": True},
            {"name": "taker",        "type": "address", "indexed": True},
            {"name": "makerAssetId", "type": "uint256", "indexed": False},
            {"name": "takerAssetId", "type": "uint256", "indexed": False},
            {"name": "makerAmount",  "type": "uint256", "indexed": False},
            {"name": "takerAmount",  "type": "uint256", "indexed": False},
            {"name": "fee",          "type": "uint256", "indexed": False},
        ]
    }
    
    decoded = W3_CLIENT.eth.contract(abi=[ORDER_FILLED_ABI]).events.OrderFilled().process_log({
        "data": log["data"],
        "topics": [bytes.fromhex(t[2:]) for t in log["topics"]],
        "address": log["address"],
        "blockHash": log.get("blockHash", "0x"),
        "transactionHash": log.get("transactionHash", "0x"),
        "logIndex": log.get("logIndex", "0x0"),
        "blockNumber": log.get("blockNumber", "0x0"),
        "transactionIndex": log.get("transactionIndex", "0x0"),
    })

    args = decoded["args"]
    maker        = args["maker"]
    taker        = args["taker"]
    maker_asset  = args["makerAssetId"]
    taker_asset  = args["takerAssetId"]
    maker_amount = args["makerAmount"] / 1e6
    taker_amount = args["takerAmount"] / 1e6
    tx           = log["transactionHash"]

    # print(taker_asset)
    # print(maker_asset)

    if maker_asset == 0:
        print(f"* Buy: {maker_amount}")
        token_id = str(taker_asset)
        await asyncio.get_event_loop().run_in_executor(
            None, poly_buy, tx, maker, taker, token_id, maker_amount
        )
    else:
        print(f"* Sell: {taker_amount}")
        token_id = str(maker_asset)
        await asyncio.get_event_loop().run_in_executor(
            None, poly_sell, tx, maker, taker, token_id, taker_amount
        )

    # print data
    with lock:
        snapshot = trades.copy()
    for trade in snapshot:
        if trade.printed is False:
            trade.debug()
            trade.printed = True

# defs
def get_shares(amount: float, price: float):
    shares = amount / price
    return max(shares, 5)
def find_by_tx_hash(data, tx_hash):
    return next((e for e in data if e["transactionHash"] == tx_hash), None)
def get_winrate(limit, offset):
    activity = get_activity(limit, offset)
    index = 0
    trades = 0
    wins = 0
    losses = 0

    for i in activity:
        slug = i.get("slug")
        outcome = i.get("outcome")
        title = i.get("title")
        winner = get_market_winner(slug)

        if winner is not None:
            print(f"{index} of {limit}")
            print(title)
            print(slug)
            if outcome == winner:
                print("Win :)")
                wins += 1
            else:
                print("Loss :(")
                losses += 1
            print("---")
            trades += 1

        index += 1

    print(f"Trades: {trades}")
    print(f"Wins: {wins}")
    print(f"Losses: {losses}")
    winrate = wins / (wins + losses)
    winrate = winrate * 100
    print(f"Winrate: {winrate:.2f}%")
async def wb_start():
    async with websockets.connect(POLYGON_WSS) as ws:
        await subscribe(ws)
        try:
            await listen(ws)
        except KeyboardInterrupt:
            print("\nStopped.")
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--redeem", type=str)
    args = parser.parse_args()
    return args
def print_scale_info():
    print("Scale info:")

    invested = calc_scaled_invested(1, TRADER_MIN, TRADER_MAX, MIN, MAX)
    print(f"* Trader buy 1 USDC, You buy {invested:.2f} USDC")

    invested = calc_scaled_invested(5, TRADER_MIN, TRADER_MAX, MIN, MAX)
    print(f"* Trader buy 5 USDC, You buy {invested:.2f} USDC")

    invested = calc_scaled_invested(10, TRADER_MIN, TRADER_MAX, MIN, MAX)
    print(f"* Trader buy 10 USDC, You buy {invested:.2f} USDC")

    invested = calc_scaled_invested(20, TRADER_MIN, TRADER_MAX, MIN, MAX)
    print(f"* Trader buy 20 USDC, You buy {invested:.2f} USDC")

    invested = calc_scaled_invested(50, TRADER_MIN, TRADER_MAX, MIN, MAX)
    print(f"* Trader buy 50 USDC, You buy {invested:.2f} USDC")

    invested = calc_scaled_invested(100, TRADER_MIN, TRADER_MAX, MIN, MAX)
    print(f"* Trader buy 100 USDC, You buy {invested:.2f} USDC")

    invested = calc_scaled_invested(1000, TRADER_MIN, TRADER_MAX, MIN, MAX)
    print(f"* Trader buy 1000 USDC, You buy {invested:.2f} USDC")

    print("----")
def redeem_loop():
    global last_balance

    while True:
        try:
            redeem_wins_class_2()
            save_trades(DATA_FILENAME) # backup data

        except Exception as e:
            print("Error: ", e)

        time.sleep(REDEEM_COOLDOWN * 60)
def poly_buy(tx_hash, from_hash, to_hash, token_id, amount, retry = 0):
    global last_balance
    global trades



    if retry == RETRY_COUNT:
        print("Max retries reached for buy. Skipping.")
        return



    start_time = time.time()
    trade = Trade()
    utc = get_utc_time()



    if amount < MIN_TRADER_AMOUNT:
        print("Trader amount is less than your min. amount.")
        return



    # fill class
    trade.tx_hash = tx_hash
    trade.from_hash = from_hash
    trade.to_hash = to_hash
    trade.token_id = token_id
    trade.amount = amount
    trade.utc = datetime_to_str(utc)
    trade.side = "Buy"



    # is token valid?
    if token_id is None:
        print("Token is not valid.")
        return



    same_orders = 0
    with lock:
        same_orders = count_same_token_ids(trades, token_id)
    if same_orders >= MAX_DUPLICATE_POSITIONS:
        print("Order is already created by token id.")
        return



    # amount to buy
    your_amount = 0
    if MODE == "FIXED":
        your_amount = FIXED
    elif MODE == "AUTO":
        your_amount = calc_scaled_invested(amount, TRADER_MIN, TRADER_MAX, MIN, MAX)
    else:
        print("Wrong mode.")
        return
    trade.your_amount = your_amount



    # run all in same time and wait for all to finish
    with concurrent.futures.ThreadPoolExecutor() as executor:
        f_data = executor.submit(get_market_info_from_token_id, token_id)
        f_price = executor.submit(get_price, token_id)
        f_slippage = executor.submit(check_slippage, token_id, your_amount, "BUY", MAX_SLIPPAGE)
        f_liq = executor.submit(get_available_liquidity, token_id, "Buy")

        data = f_data.result()
        price = f_price.result()
        slippage_ok = f_slippage.result()
        last_liq = f_liq.result()



    slug = get_slug_from_data(data)
    side_str = get_side_str_from_data(data, token_id)
    trade.slug = slug
    trade.side_str = side_str
    trade.price = price
    trade.last_liq = last_liq
    condition_id = get_condition_id(data)
    trade.condition_id = condition_id
    trade.title = get_title_from_data(data)


    
    if ALLOWED_HOURS:
        hour = get_hour_from_slug(slug)
        if hour not in ALLOWED_HOURS:
            data.remove(entry)
            print("This hour is not allowed.")
            return



    price = 0
    if USE_LIMIT_ORDERS:
        sleep(5) # 1
        activity_data = get_activity_by_condition_id(condition_id)
        if not activity_data:
            print("x")
            sleep(5) # 2
            activity_data = get_activity_by_condition_id(condition_id)
        if not activity_data:
            print("x")
            sleep(5) # 3
            activity_data = get_activity_by_condition_id(condition_id)
        if not activity_data:
            print("x")
            sleep(5) # 4
            activity_data = get_activity_by_condition_id(condition_id)
        if not activity_data:
            return 
        if activity_data:
            x = find_by_tx_hash(activity_data, tx_hash)
            if x:
                price = x["price"]

        # print(price)



    with lock:
        same_orders = count_same_slugs(trades, slug)
    if same_orders >= MAX_DUPLICATE_POSITIONS_SLUG:
        print("Order is already created by slug.")
        return



    # turn off
    if contains_word(slug, "btc"):
        if not ENABLE_BTC:
            return
    elif contains_word(slug, "eth"):
        if not ENABLE_ETH:
            return
    elif contains_word(slug, "sol"):
        if not ENABLE_SOL:
            return
    elif contains_word(slug, "xrp"):
        if not ENABLE_XRP:
            return
    elif contains_word(slug, "doge"):
        if not ENABLE_DOGE:
            return
    else:
        if not ENABLE_OTHER_MARKETS:
            return



    # is market active?
    if is_market_active_from_data(data) is False:
        print("Market is closed.")
        return
    # is liquidity enough?
    if last_liq < your_amount:
        print("Low liquidity.")
        return
    # is slippage ok?
    if not slippage_ok:
        print("Slippage is not good.")
        return



    try:
        if ENABLE_TRADING:
            if last_liq < your_amount: # enough liquidity?
                your_amount = last_liq # adjust amount to liquidity

            if USE_LIMIT_ORDERS:
                if price != 0:
                    shares = get_shares(your_amount, price)
                    order = create_polymarket_limit_order(token_id, shares, "BUY", price)
                    trade.order = order
                    print(order)
            else: # market order
                order = create_polymarket_market_order(token_id, your_amount, "BUY")
                trade.order = order
                print(order)

            trade.trading_enabled = True # successfully created order



    # clob exception
    except Exception as e:
        error_msg = str(e).lower()
        trade.error = error_msg
        # print(error_msg)
        trade.trading_enabled = False # failed to create order
        print(f"Some error: {error_msg}")

        print("Try again.")
        poly_buy(tx_hash, from_hash, to_hash, token_id, amount, retry + 1)
        return



    # calculate time
    end_time = time.time()
    trade.timex = f"{(end_time - start_time) * 1000:.2f}ms"



    # append trade to list
    with lock:
        trades.append(trade)

    if ONLY_ONE_ORDER:
        sys.exit(0) # 1 test
        os.kill(os.getpid(), signal.SIGINT) # 2 test
def poly_sell(tx_hash, from_hash, to_hash, token_id, amount, retry = 0):
    global last_balance
    global trades

    if retry == RETRY_COUNT:
        print("Max retries reached for buy. Skipping.")
        return

    # is token valid?
    if token_id is None:
        return



    if BLOCK_SELL_POSITIONS:
        return



    start_time = time.time()
    with lock:
        trade = get_trade_by_token_id(token_id, "Buy")
    if trade is None:
        return
    utc = get_utc_time()



    # amount to sell
    your_amount = 0
    if MODE == "FIXED":
        your_amount = FIXED
    elif MODE == "AUTO":
        your_amount = calc_scaled_invested(amount, TRADER_MIN, TRADER_MAX, 0, 9999)
    else:
        return



    # you can not sell more than you buy
    if your_amount > trade.your_amount:
        your_amount = trade.your_amount



    # run all in same time and wait for all to finish
    with concurrent.futures.ThreadPoolExecutor() as executor:
        f_data = executor.submit(get_market_info_from_token_id, token_id)
        # f_price = executor.submit(get_price, token_id)
        f_slippage = executor.submit(check_slippage, token_id, your_amount, "SELL", MAX_SLIPPAGE)
        f_liq = executor.submit(get_available_liquidity, token_id, "Sell")

        data = f_data.result()
        # price = f_price.result()
        slippage_ok = f_slippage.result()
        last_liq = f_liq.result()



    # slug = get_slug_from_data(data)
    # side_str = get_side_str_from_data(data, token_id)
    # trade.slug = slug
    # trade.side_str = side_str
    # trade.price = price
    # trade.last_liq = last_liq



    # is market active?
    if is_market_active_from_data(data) is False:
        return
    # is liquidity enough?
    if last_liq < your_amount:
        return
    # is slippage ok?
    if not slippage_ok:
        return



    try:
        if ENABLE_TRADING:
            if trade.trading_enabled:
                if last_liq < your_amount:   # enough liquidity?
                    your_amount = last_liq   # adjust amount to liquidity

                order = create_polymarket_market_order(token_id, your_amount, "SELL")
                trade.order = order
                print(order)



    # clob exception
    except Exception as e:
        error_msg = str(e).lower()
        trade.error = error_msg

        print("Try again.")
        poly_sell(tx_hash, from_hash, to_hash, token_id, amount, retry + 1)
        return



    # calculate time
    end_time = time.time()
    trade.timex = f"{(end_time - start_time) * 1000:.2f}ms"
def check_slippage(token_id: str, usdc_amount: float, side: str, max_slippage: float = 0.01):
    try:
        book = POLYMARKET_CLIENT.get_order_book(token_id)
    except Exception as e:
        return False

    if side == "BUY":
        if not book.asks:
            return False
        orders = sorted(book.asks, key=lambda x: float(x.price))
        best_price = float(orders[0].price)
    else:  # SELL
        if not book.bids:
            return False
        orders = sorted(book.bids, key=lambda x: float(x.price), reverse=True)
        best_price = float(orders[0].price)

    remaining = usdc_amount
    total_shares = 0

    for order in orders:
        price = float(order.price)
        available_usdc = float(order.size) * price

        if remaining <= available_usdc:
            total_shares += remaining / price
            remaining = 0
            break
        else:
            total_shares += float(order.size)
            remaining -= available_usdc

    if remaining > 0:
        return False

    if total_shares == 0:
        return False

    avg_price = usdc_amount / total_shares
    slippage = abs(avg_price - best_price)

    if slippage > max_slippage:
        return False

    return True


def wait_until_next_5min_2(seconds_before: int = 0):
    now_utc = get_utc_time()
    next_5 = floor_minutes_to_nearest_5(now_utc) + timedelta(minutes=5)
    trigger = next_5 - timedelta(seconds=seconds_before)
    wait_seconds = (trigger - now_utc).total_seconds()
    
    if wait_seconds < 0:
        next_5 += timedelta(minutes=5)
        trigger = next_5 - timedelta(seconds=seconds_before)
        wait_seconds = (trigger - now_utc).total_seconds()
    
    print(f"Waiting {wait_seconds:.0f}s until {trigger}")
    time.sleep(wait_seconds)
def get_prediction_index(data, threshold):
    if not data:
        return None
    
    if data["up_pct"] >= threshold:
        return 0 # Up
    elif data["down_pct"] >= threshold:
        return 1 # Down
    else:
        return None
def wait_until_next_5min():
    now_utc = get_utc_time()
    next_5 = floor_minutes_to_nearest_5(now_utc) + timedelta(minutes=5)
    wait_seconds = (next_5 - now_utc).total_seconds()
    print(f"Waiting {wait_seconds:.0f}s")
    time.sleep(wait_seconds)
def predict_next(history: list):
    if not history:
        return None
    
    resolved = [x for x in history if x["winner"] is not None]
    total = len(resolved)
    
    if total == 0:
        return None
    
    ups = sum(1 for x in resolved if x["winner"] == 0)
    downs = total - ups
    
    up_pct = ups / total * 100
    down_pct = downs / total * 100
    
    return {
        "up_pct": round(up_pct, 1),
        "down_pct": round(down_pct, 1),
        "prediction": "Up" if up_pct > down_pct else "Down",
        "samples": total
    }
def get_history_5m(limit: int, from_utc, slug_name):
    now_utc = from_utc
    round_utc = floor_minutes_to_nearest_5(now_utc)
    
    data = []
    
    for i in range(limit):
        sub = subtract_5_minutes(round_utc)
        round_utc = sub
        timestamp = get_timestamp_from_datetime(sub)
        slug = f"{slug_name}-{timestamp}"
        
        market_info = get_market_info(slug)
        win_side_index = get_win_side_index(market_info)
        up_id = get_token_id_from_side(market_info, 0)
        down_id = get_token_id_from_side(market_info, 1)
        up_price = get_last_price(up_id)
        down_price = get_last_price(down_id)
        result = get_winner(up_price, down_price)

        win_str = "Up" if result == 0 else "Down" if result == 1 else None

        data.append({
            "slug": slug,
            "timestamp": timestamp,
            "up_price": up_price,
            "down_price": down_price,
            "winner": result,
            "win_str": win_str,
            "datetime": datetime_to_str(sub),
        })
    
    return data
def test1_2_backtest(limit: int, slug_name):
    win = 0
    loss = 0
    skip = 0

    start_timestamp = 1775146500
    datetime = get_utc_from_timestamp(start_timestamp) # from start

    for i in range(limit):
        print(i)
        history = get_history_5m(SAMPLES, datetime, slug_name)
        predict = predict_next(history)
        index = get_prediction_index(predict, THRESHOLD)
        print(predict)
        timestamp = get_timestamp_from_datetime(datetime)
        slug = f"{slug_name}-{timestamp}"
        # print(slug)
        data = get_market_info(slug)
        win_index = get_win_side_index(data)
        print(f"Real win: {win_index}")

        if index is not None:
            win_str = "Up" if index == 0 else "Down" if index == 1 else None
            print(f"** {win_str} **")
            if win_str == win_index:
                win += 1
            else:
                loss += 1
        else:
            skip += 1

        datetime = subtract_5_minutes(datetime)
        print("----")

    win_rate = win / (win + loss) * 100 if (win + loss) > 0 else 0
    total = win + loss + skip
    print(f"SAMPLES: {SAMPLES}")
    print(f"THRESHOLD: {THRESHOLD}")
    print(f"Total: {total}")
    print(f"Win: {win}")
    print(f"Loss: {loss}")
    print(f"Skip: {skip}")
    print(f"Winrate: {win_rate:.2f}%")
def get_auto_amount(up_price, down_price, min_amount, max_amount):
    winning_price = max(up_price, down_price)
    losing_price = min(up_price, down_price)
    confidence = winning_price - losing_price
    return round(max(min_amount, min_amount + confidence * (max_amount - min_amount)), 2)
def scale_profit(win_profit, original_amount, new_amount):
    original_profit = win_profit - original_amount
    scaled = original_profit * (new_amount / original_amount)
    return round(new_amount + scaled, 2)
def test1_2(slug_name):
    now_utc = get_utc_time()
    history = get_history_5m(SAMPLES, now_utc, slug_name)
    predict = predict_next(history)
    index = get_prediction_index(predict, THRESHOLD)

    now_utc_str = datetime_to_str(now_utc)
    round_utc = floor_minutes_to_nearest_5(now_utc)
    timestamp = get_timestamp_from_datetime(round_utc)
    slug = f"{slug_name}-{timestamp}"
    data = get_market_info(slug)
    your_amount = FIXED

    print(f"Prediction data: {predict}")
    print(f"Slug: {slug}")
    print(f"Your amount: {your_amount}")
    print(f"Datetime: {now_utc_str}")

    if index is not None:
        token_id = get_token_id_from_side(data, index)
        price = get_price(token_id)
        win_price = get_win_price(price, your_amount)

        win_str = "Up" if index == 0 else "Down" if index == 1 else None

        print(f"Token id: {token_id}")
        print(f"Index: {index}")
        print(f"Side: {win_str}")
        print(f"Price: {price}")
        print(f"Win price: {win_price}")

        if ENABLE_TRADING:
            order = create_polymarket_market_order(token_id, your_amount, "BUY")
            print(order)

    print("----")
def test1():
    print("Test 1 running...")
    print(f"Waiting time is {WAIT_TIME} seconds.")
    # test1_2(BTC_UPDOWN_5M)
    # test1_2_backtest(100, ETH_UPDOWN_5M)
    # return
    
    try:
        while True:
            # test 1
            # wait_until_next_5min()
            # test1_2(BTC_UPDOWN_5M)
            # test 2
            wait_until_next_5min_2(WAIT_TIME)
            test2(BTC_UPDOWN_5M)
            test2(ETH_UPDOWN_5M)
            test2(SOL_UPDOWN_5M)
            test2(XRP_UPDOWN_5M)
            # test2(DOGE_UPDOWN_5M)
            save_data(DATA_FILENAME)
    except KeyboardInterrupt:
        print("Stopped.")




# ----------------------------
def run_backtest_from_file():
    win = 0
    loss = 0
    skip = 0
    total_profit = 0

    btc_win = 0
    btc_loss = 0
    btc_profit = 0
    eth_win = 0
    eth_loss = 0
    eth_profit = 0
    sol_win = 0
    sol_loss = 0
    sol_profit = 0
    xrp_win = 0
    xrp_loss = 0
    xrp_profit = 0
    doge_win = 0
    doge_loss = 0
    doge_profit = 0

    for entry in trades:
        slug = entry.slug
        price = entry.price
        side_str = entry.side_str
        trader_amount = entry.amount
        your_amount = entry.your_amount

        if USE_YOUR_AMOUNT_BACKTEST:
            auto_amount = your_amount
        else:
            auto_amount = trader_amount

        data = get_event_info(slug)
        title = data[0]['title']
        win_str = get_win_side_str_from_event_data(data)

        return_amount = get_win_price(price, auto_amount) # !!!
        net_profit = return_amount - auto_amount

        if win_str is not None:
            if win_str == side_str:
                win += 1
                total_profit += net_profit
                print(f"+ Win: {slug}, Amount: {auto_amount:.2f}, Profit: {net_profit:.2f}, Return: {return_amount:.2f}, Title: {title}, Price: {(price * 100):.2f}")

                if contains_word(slug, "btc"):
                    btc_win += 1
                    btc_profit += net_profit
                elif contains_word(slug, "eth"):
                    eth_win += 1
                    eth_profit += net_profit
                elif contains_word(slug, "sol"):
                    sol_win += 1
                    sol_profit += net_profit
                elif contains_word(slug, "xrp"):
                    xrp_win += 1
                    xrp_profit += net_profit
                elif contains_word(slug, "doge"):
                    doge_win += 1
                    doge_profit += net_profit
            else:
                loss += 1
                total_profit -= auto_amount
                print(f"- Loss: {slug}, Amount: {auto_amount:.2f}, Profit: {-auto_amount:.2f}, Return: {-auto_amount:.2f}, Title: {title}, Price: {(price * 100):.2f}")

                if contains_word(slug, "btc"):
                    btc_loss += 1
                    btc_profit -= auto_amount
                elif contains_word(slug, "eth"):
                    eth_loss += 1
                    eth_profit -= auto_amount
                elif contains_word(slug, "sol"):
                    sol_loss += 1
                    sol_profit -= auto_amount
                elif contains_word(slug, "xrp"):
                    xrp_loss += 1
                    xrp_profit -= auto_amount
                elif contains_word(slug, "doge"):
                    doge_loss += 1
                    doge_profit -= auto_amount
        else:
            skip += 1

    print("----")

    total = win + loss
    win_rate = (win / total * 100) if total > 0 else 0
    print(f"Total: {total}")
    print(f"Total win: {win}")
    print(f"Total loss: {loss}")
    print(f"Total skip: {skip}")
    print(f"Total winrate: {win_rate:.2f}%")
    print(f"Total profit: {total_profit:.2f} USDC")

    print("----")

    print("")
    print(f"BTC win: {btc_win} loss: {btc_loss}")
    total = btc_win + btc_loss
    win_rate = (btc_win / total * 100) if total > 0 else 0
    print(f"Winrate: {win_rate:.2f}%")
    print(f"BTC profit: {btc_profit:.2f} USDC")
    print("")

    print(f"ETH win: {eth_win} loss: {eth_loss}")
    total = eth_win + eth_loss
    win_rate = (eth_win / total * 100) if total > 0 else 0
    print(f"Winrate: {win_rate:.2f}%")
    print(f"ETH profit: {eth_profit:.2f} USDC")
    print("")

    print(f"SOL win: {sol_win} loss: {sol_loss}")
    total = sol_win + sol_loss
    win_rate = (sol_win / total * 100) if total > 0 else 0
    print(f"Winrate: {win_rate:.2f}%")
    print(f"SOL profit: {sol_profit:.2f} USDC")
    print("")

    print(f"XRP win: {xrp_win} loss: {xrp_loss}")
    total = xrp_win + xrp_loss
    win_rate = (xrp_win / total * 100) if total > 0 else 0
    print(f"Winrate: {win_rate:.2f}%")
    print(f"XRP profit: {xrp_profit:.2f} USDC")
    print("")

    print(f"DOGE win: {doge_win} loss: {doge_loss}")
    total = doge_win + doge_loss
    win_rate = (doge_win / total * 100) if total > 0 else 0
    print(f"Winrate: {win_rate:.2f}%")
    print(f"DOGE profit: {doge_profit:.2f} USDC")
    print("")
def test2_1(slug_name, sleep_time, retry, max_retry):
    if retry == max_retry:
        return

    # get utc time
    now_utc = get_utc_time()
    # datetime to str
    now_utc_str = datetime_to_str(now_utc)
    # round datetime
    round_utc = floor_minutes_to_nearest_5(now_utc)
    # get timestamp from datetime
    timestamp = get_timestamp_from_datetime(round_utc)

    slug = f"{slug_name}-{timestamp}"
    data = get_market_info(slug)
    your_amount = FIXED


    if is_market_closed(data):
        print(f"* Market is closed.")
        return



    token_id_up = get_token_id_from_side(data, 0)
    token_id_down = get_token_id_from_side(data, 1)
    up_price = get_price(token_id_up)
    down_price = get_price(token_id_down)
    win_profit = 0
    win_side = ""



    # win profit filter
    if WIN_PROFIT_THRESHOLD != 0.0:
        val = 1
        if up_price > down_price:
            win_profit = get_win_price(up_price, val)
        else:
            win_profit = get_win_price(down_price, val)

        if win_profit > WIN_PROFIT_THRESHOLD:
            print("Skip - too uncertain.")
            return



    # scale auto amount based of market
    if MODE == "AUTO":
        your_amount = get_auto_amount(down_price, up_price, MIN, MAX)



    # fast flag
    if True:
        if abs(up_price - down_price) > 0.20:
            print("Retry, market too one-sided.")
            time.sleep(sleep_time)
            test2_1(slug_name, sleep_time, retry + 1, max_retry)
            return



    print(f"* Slug: {slug}")
    print(f"* Your amount: {your_amount}")
    print(f"* Datetime: {now_utc_str}")



    if up_price > down_price:
        print("* Up is winning...")
        print(f"* Price: {up_price}")
        win_profit = get_win_price(up_price, your_amount)
        print(f"* Win price: {win_profit}")
        win_side = "Up"
        token_id = token_id_up
    else:
        print("* Down is winning...")
        print(f"* Price: {down_price}")
        win_profit = get_win_price(down_price, your_amount)
        print(f"* Win price: {win_profit}")
        win_side = "Down"
        token_id = token_id_down



    trading_enabled = False



    # create and post order
    if ENABLE_TRADING:
        liq = get_available_liquidity(token_id)
        if liq < your_amount:
            print(f"* Not enough liquidity.")
        else:
            try:
                order = create_polymarket_market_order(token_id, your_amount, "BUY")
                print(f"* Order created: {slug}")
                print(order)
                trading_enabled = True
            except Exception as e:
                print(f"Order failed: {e}")
                trading_enabled = False



    # save data
    entry = {
        "slug": slug,
        "datetime": now_utc_str,
        "amount": your_amount,
        "win_profit": win_profit,
        "win_side": win_side,
        "up_price": up_price,
        "down_price": down_price,
        "token_id": token_id,
        "trading_enabled": trading_enabled,
        "redeemed": False,
        "closed": False,
    }
    with lock:
        DATA.append(entry)

    print("----")
def test2(slug_name):
    # get utc time
    now_utc = get_utc_time()
    # datetime to str
    now_utc_str = datetime_to_str(now_utc)
    # round datetime
    round_utc = floor_minutes_to_nearest_5(now_utc)
    # get timestamp from datetime
    timestamp = get_timestamp_from_datetime(round_utc)

    slug = f"{slug_name}-{timestamp}"
    data = get_market_info(slug)
    your_amount = FIXED



    token_id_up = get_token_id_from_side(data, 0)
    token_id_down = get_token_id_from_side(data, 1)
    up_price = get_price(token_id_up)
    down_price = get_price(token_id_down)
    win_profit = 0
    win_side = ""



    # win profit filter
    if WIN_PROFIT_THRESHOLD != 0.0:
        val = 1
        if up_price > down_price:
            win_profit = get_win_price(up_price, val)
        else:
            win_profit = get_win_price(down_price, val)

        if win_profit > WIN_PROFIT_THRESHOLD:
            print("Skip - too uncertain.")
            return



    # scale auto amount based of market
    if MODE == "AUTO":
        your_amount = get_auto_amount(down_price, up_price, MIN, MAX)



    print(f"* Slug: {slug}")
    print(f"* Your amount: {your_amount}")
    print(f"* Datetime: {now_utc_str}")



    if up_price > down_price:
        print("* Up is winning...")
        print(f"* Price: {up_price}")
        win_profit = get_win_price(up_price, your_amount)
        print(f"* Win price: {win_profit}")
        win_side = "Up"
    else:
        print("* Down is winning...")
        print(f"* Price: {down_price}")
        win_profit = get_win_price(down_price, your_amount)
        print(f"* Win price: {win_profit}")
        win_side = "Down"



    token_id = token_id_up if win_side == "Up" else token_id_down
    trading_enabled = False

    # create and post order
    if ENABLE_TRADING:
        liq = get_available_liquidity(token_id)
        if liq < your_amount:
            print(f"* Not enough liquidity.")
        else:
            try:
                order = create_polymarket_market_order(token_id, your_amount, "BUY")
                print(f"* Order created: {slug}")
                print(order)
                trading_enabled = True
            except Exception as e:
                print(f"Order failed: {e}")
                trading_enabled = False



    # save data
    entry = {
        "slug": slug,
        "datetime": now_utc_str,
        "amount": your_amount,
        "win_profit": win_profit,
        "win_side": win_side,
        "up_price": up_price,
        "down_price": down_price,
        "token_id": token_id,
        "trading_enabled": trading_enabled,
        "redeemed": False,
        "closed": False,
    }
    with lock:
        DATA.append(entry)

    print("----")
def redeem_wins():
    global last_balance

    if not REDEEM_POSITIONS:
        return
    
    some_redeemed = False

    with lock:
        entries = list(DATA)



    for entry in entries:
        slug = entry.get("slug")
        win_side = entry.get("win_side")
        token_id = entry.get("token_id")
        trading_enabled = entry.get("trading_enabled")
        redeemed = entry.get("redeemed")
        closed = entry.get("closed")



        if trading_enabled and not redeemed and not closed:
            data = get_market_info(slug)
            if is_market_closed(data):
                with lock:
                    entry["closed"] = True

                # if is_win_market(data, win_side):
                with lock:
                    entry["redeemed"] = True

                if need_to_redeem(token_id):
                    condition_id = get_condition_id(data)
                    redeem_position(condition_id)
                    some_redeemed = True
                    print("Redeemed: ", slug)

    if some_redeemed:
        new_balance = get_balance()
        with lock_balance:
            last_balance = new_balance
def redeem_wins_class():
    global last_balance
    global trades
    
    some_redeemed = False

    with lock:
        entries = list(trades)



    for entry in entries:
        slug = entry.slug
        win_side = entry.side_str
        token_id = entry.token_id
        trading_enabled = entry.trading_enabled
        redeemed = entry.redeemed
        closed = entry.closed



        if trading_enabled and not redeemed and not closed:
            data = get_event_info(slug)
            if data:
                if is_market_closed(data): # check 1
                    condition_id = get_condition_id_from_event(data)
                    if can_redeem(condition_id): # check 2
                        with lock:
                            entry.closed = True
                            entry.redeemed = True

                        if need_to_redeem(token_id): # check 3
                            redeem_position(condition_id)
                            some_redeemed = True
                            print(f"Redeemed: {slug}")

    if some_redeemed:
        new_balance = get_balance()
        with lock_balance:
            last_balance = new_balance
def redeem_wins_class_2():
    global last_balance
    global trades
    global redeem_list


    some_redeemed = False
    active_orders = get_active_orders()



    for entry in active_orders:
        slug = entry["slug"]
        redeemable = entry["redeemable"]
        token_id = entry["asset"]
        condition_id = entry["conditionId"]

        if redeemable:
            if condition_id in redeem_list: # already redeemed / bug fix
                continue
            if can_redeem(condition_id): # check 1
                if need_to_redeem(token_id): # check 2
                    redeem_position(condition_id)
                    some_redeemed = True
                    print(f"Redeemed: {slug}")
                    redeem_list[condition_id] = True



    if some_redeemed:
        new_balance = get_balance()
        with lock_balance:
            last_balance = new_balance
def test3():
    print("Test 3 running...")
    
    def run_coin(slug, wait_time):
        try:
            while True:
                wait_until_next_5min_2(wait_time)
                test2_1(slug, 5, 0, 5)
                with lock:
                    save_data(DATA_FILENAME)
        except KeyboardInterrupt:
            pass

    def run_redeem(wait_time):
        try:
            while True:
                wait_until_next_5min_2(wait_time)
                redeem_wins()
        except KeyboardInterrupt:
            pass
    
    threads = [
        threading.Thread(target=run_coin, args=(BTC_UPDOWN_5M, 30)),
        # threading.Thread(target=run_coin, args=(ETH_UPDOWN_5M, 30)),
        # threading.Thread(target=run_coin, args=(SOL_UPDOWN_5M, 60)),
        # threading.Thread(target=run_coin, args=(XRP_UPDOWN_5M, 60)),
        # threading.Thread(target=run_coin, args=(DOGE_UPDOWN_5M, 60)),
        # threading.Thread(target=run_redeem, args=(60,)),
    ]
    
    for t in threads:
        t.daemon = True
        t.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopped.")
# ----------------------------

def parse_wallets(env_value: str):
    raw = [w.strip().lower() for w in env_value.split(",") if w.strip()]
    return len(raw) != len(set(raw))
def is_account_active(n: int = 5):
    trades = get_closed_trades2(n)
    
    if not trades:
        return False
    
    today_utc = datetime.now(timezone.utc).date()
    
    for trade in trades:
        timestamp = trade.get("timestamp")
        if timestamp:
            trade_date = datetime.fromtimestamp(timestamp, tz=timezone.utc).date()
            if trade_date == today_utc:
                return True
    
    return False

def start():
    global last_balance
    global trades

    print("Starting...")
    print("----")
    load_dotenv(".env")

    # load data from file
    load_trades(DATA_FILENAME)

    # globals 
    global WALLETS_TO_COPY
    global POLYGON_RPC
    global POLYGON_WSS
    global PUBLIC_KEY
    global PRIVATE_KEY
    global FIXED
    global MIN
    global MAX
    global SCALE
    global MODE
    global RATIO_FOR_TRADE
    global ENABLE_TRADING
    global ORDER_TYPE
    global SHARES
    global RUN_BACKTEST_FILE
    global RUN_BACKTEST_URL
    global REDEEM_POSITIONS
    global BACKTEST_BALANCE
    global BACKTEST_LIMIT
    global MAX_SLIPPAGE
    global REDEEM_COOLDOWN
    global LIMIT_PRICE
    global ENABLE_COPY_TRADE
    global ENABLE_TEST1
    global SAMPLES
    global THRESHOLD
    global WAIT_TIME
    global FUNDER_PUBLIC_KEY
    global WIN_PROFIT_THRESHOLD
    global ENABLE_BTC
    global ENABLE_ETH
    global ENABLE_SOL
    global ENABLE_XRP
    global ENABLE_DOGE
    global TRADER_MIN
    global TRADER_MAX
    global MIN_TRADER_AMOUNT
    global MAX_DUPLICATE_POSITIONS
    global BLOCK_SELL_POSITIONS
    global USE_YOUR_AMOUNT_BACKTEST
    global ENABLE_OTHER_MARKETS
    global USE_WORSE_ENTRY
    global USE_WORSE_PNL
    global MAX_DUPLICATE_POSITIONS_SLUG
    global USE_LIMIT_ORDERS
    global FILTER_TRADES_BY_TITLE
    global ALLOWED_HOURS
    global FILTER_TRADES_BY_YOUR_TRADES
    global AUTO_FIND_BY_LEADBOARD
    global LEADBOARD_CATEGORY
    global LEADBOARD_TIME_PERIOD
    global LEADBOARD_LIMIT
    global WALLETS_TO_COPY_2
    global SKIP_NOT_PROFIT_WALLETS
    global ONLY_ONE_ORDER
    global RETRY_COUNT


    # load data from .env
    WALLETS_TO_COPY = get_env_value("WALLET_TO_COPY")
    print(f"Wallet to copy: {WALLETS_TO_COPY}")

    POLYGON_RPC = get_env_value("POLYGON_RPC")
    POLYGON_WSS = get_env_value("POLYGON_WSS")
    PUBLIC_KEY = get_env_value("PUBLIC_KEY")
    PRIVATE_KEY = get_env_value("PRIVATE_KEY")
    FIXED = float(get_env_value("FIXED"))
    MIN = float(get_env_value("YOUR_MIN"))
    MAX = float(get_env_value("YOUR_MAX"))
    SCALE = 1
    MODE = get_env_value("MODE")
    RATIO_FOR_TRADE = 0.0
    ENABLE_TRADING = get_env_value("ENABLE_TRADING").lower() in ("1", "true") # bool
    ORDER_TYPE = "MARKET"
    SHARES = 5
    RUN_BACKTEST_FILE = get_env_value("RUN_BACKTEST_FILE").lower() in ("1", "true") # bool
    RUN_BACKTEST_URL = get_env_value("RUN_BACKTEST_URL").lower() in ("1", "true") # bool
    REDEEM_POSITIONS = get_env_value("REDEEM_POSITIONS").lower() in ("1", "true") # bool
    BACKTEST_BALANCE = float(get_env_value("BACKTEST_BALANCE"))
    BACKTEST_LIMIT = int(get_env_value("BACKTEST_LIMIT"))
    MAX_SLIPPAGE = float(get_env_value("MAX_SLIPPAGE"))
    REDEEM_COOLDOWN = get_env_value("REDEEM_COOLDOWN").lower() in ("1", "true") # bool
    LIMIT_PRICE = 0.5
    ENABLE_COPY_TRADE = get_env_value("ENABLE_COPY_TRADE").lower() in ("1", "true") # bool
    ENABLE_TEST1 = False
    SAMPLES = 3
    THRESHOLD = 70
    WAIT_TIME = 60
    FUNDER_PUBLIC_KEY = get_env_value("FUNDER_PUBLIC_KEY")
    WIN_PROFIT_THRESHOLD = 0.0
    ENABLE_BTC = get_env_value("ENABLE_BTC").lower() in ("1", "true") # bool
    ENABLE_ETH = get_env_value("ENABLE_ETH").lower() in ("1", "true") # bool
    ENABLE_SOL = get_env_value("ENABLE_SOL").lower() in ("1", "true") # bool
    ENABLE_XRP = get_env_value("ENABLE_XRP").lower() in ("1", "true") # bool
    ENABLE_DOGE = get_env_value("ENABLE_DOGE").lower() in ("1", "true") # bool
    TRADER_MIN = float(get_env_value("TRADER_MIN"))
    TRADER_MAX = float(get_env_value("TRADER_MAX"))
    MIN_TRADER_AMOUNT = float(get_env_value("MIN_TRADER_AMOUNT"))
    MAX_DUPLICATE_POSITIONS = int(get_env_value("MAX_DUPLICATE_POSITIONS_TOKEN_ID"))
    BLOCK_SELL_POSITIONS = get_env_value("BLOCK_SELL_POSITIONS").lower() in ("1", "true") # bool
    USE_YOUR_AMOUNT_BACKTEST = get_env_value("USE_YOUR_AMOUNT_BACKTEST").lower() in ("1", "true") # bool
    ENABLE_OTHER_MARKETS = get_env_value("USE_YOUR_AMOUNT_BACKTEST").lower() in ("1", "true") # bool
    USE_WORSE_ENTRY = get_env_value("USE_WORSE_ENTRY").lower() in ("1", "true") # bool
    USE_WORSE_PNL = float(get_env_value("USE_WORSE_PNL"))
    MAX_DUPLICATE_POSITIONS_SLUG = int(get_env_value("MAX_DUPLICATE_POSITIONS_SLUG"))
    USE_LIMIT_ORDERS = get_env_value("USE_LIMIT_ORDERS").lower() in ("1", "true") # bool
    FILTER_TRADES_BY_TITLE = str(get_env_value("FILTER_TRADES_BY_TITLE"))
    ALLOWED_HOURS = [int(h) for h in os.getenv("ALLOWED_HOURS", "").split(",") if h]
    FILTER_TRADES_BY_YOUR_TRADES = get_env_value("FILTER_TRADES_BY_YOUR_TRADES").lower() in ("1", "true") # bool
    AUTO_FIND_BY_LEADBOARD = get_env_value("AUTO_FIND_BY_LEADBOARD").lower() in ("1", "true") # bool
    LEADBOARD_CATEGORY = get_env_value("LEADBOARD_CATEGORY")
    LEADBOARD_TIME_PERIOD = get_env_value("LEADBOARD_TIME_PERIOD")
    LEADBOARD_LIMIT = int(get_env_value("LEADBOARD_LIMIT"))
    WALLETS_TO_COPY_2 = {w.strip().lower() for w in get_env_value("WALLETS_TO_COPY").split(",") if w.strip()}
    SKIP_NOT_PROFIT_WALLETS = get_env_value("SKIP_NOT_PROFIT_WALLETS").lower() in ("1", "true") # bool
    ONLY_ONE_ORDER = get_env_value("ONLY_ONE_ORDER").lower() in ("1", "true") # bool
    RETRY_COUNT = get_env_value("RETRY_COUNT").lower() in ("1", "true") # bool



    if parse_wallets(get_env_value("WALLETS_TO_COPY")):
        print("Duplicate wallet addresses found. Please check your .env file.")
        return



    # ping test
    ping_clob()
    print("----")

    init_w3()
    init_polymarket_client()
    allowance_info()

    # balance info
    last_balance = get_balance()
    print(f"Balance:")
    print(f"* {last_balance:.2f} USDC")
    print("----")

    print_scale_info()



    # debug
    # print(cancel_all_orders())
    # redeem_position("0xa8b04035a878ef294a570ae2412d7e477975097b3338ba077d94da0397299c2e")
    # order = create_polymarket_market_order("36968974975786888309087705623273033340448276100115729314450948790490144758499", 1.0, "BUY")
    # print(order)
    # redeem_wins_class()
    # return
    # print(pretty_print(get_leaderboard("OVERALL", "ALL", "PNL", 100)))



    # redeem wins on start
    # redeem_wins_class_2()



    if AUTO_FIND_BY_LEADBOARD:
        find_good_address()
        return
    if RUN_BACKTEST_URL:
        run_backtest_from_url(True, True, True, False)
        return
    if RUN_BACKTEST_FILE:
        run_backtest_from_file()
        return

    try:
        if REDEEM_POSITIONS:
            t = threading.Thread(target=redeem_loop, daemon=True)
            t.start()

        # run copy trading
        if ENABLE_COPY_TRADE:
            if PUBLIC_KEY == WALLETS_TO_COPY:
                print("You cannot copy trade yourself.")
                return
            asyncio.run(wb_start())

    except KeyboardInterrupt:
        save_trades(DATA_FILENAME)
        pass

start()