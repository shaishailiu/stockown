from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import json
import os
import yfinance as yf
import requests
from datetime import datetime, timedelta
import threading
import time

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

DATA_FILE = os.path.join(os.path.dirname(__file__), 'data', 'stocks.json')
CACHE_FILE = os.path.join(os.path.dirname(__file__), 'data', 'price_cache.json')

# 汇率缓存
exchange_rates = {
    'USD_HKD': 7.80,  # 默认汇率
    'HKD_HKD': 1.0,
    'last_update': None
}

# 价格最后更新时间（持久化到文件）
LAST_UPDATE_FILE = os.path.join(os.path.dirname(__file__), 'data', 'last_update.json')


def get_last_price_update():
    """从文件读取最后更新时间"""
    try:
        if os.path.exists(LAST_UPDATE_FILE):
            with open(LAST_UPDATE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('last_price_update')
    except Exception:
        pass
    return None


def set_last_price_update(timestamp):
    """将最后更新时间写入文件"""
    os.makedirs(os.path.dirname(LAST_UPDATE_FILE), exist_ok=True)
    with open(LAST_UPDATE_FILE, 'w', encoding='utf-8') as f:
        json.dump({'last_price_update': timestamp}, f, ensure_ascii=False)


def ensure_data_file():
    """确保数据文件存在"""
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False)


def load_stocks():
    """加载股票数据"""
    ensure_data_file()
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_stocks(stocks):
    """保存股票数据"""
    ensure_data_file()
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(stocks, f, ensure_ascii=False, indent=2)


def load_price_cache():
    """加载价格缓存"""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_price_cache(cache):
    """保存价格缓存"""
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def get_yfinance_symbol(code, market):
    """根据市场和代码构建 yfinance 代码"""
    if market == 'US':
        return code  # 美股直接用代码，如 AAPL, TSLA
    elif market == 'HK':
        # 港股：去掉前导零后补齐到4位 + .HK
        # 如 03690 -> 3690.HK, 0700 -> 0700.HK, 9988 -> 9988.HK
        num = str(int(code))  # 去掉所有前导零
        padded = num.zfill(4)  # 补齐到4位
        return f"{padded}.HK"
    return code


def get_exchange_rate_from_tencent():
    """通过腾讯 API 获取 USD/HKD 汇率（备用数据源）"""
    try:
        # 腾讯外汇接口：fx_susdchkd = 美元兑港币
        url = "https://qt.gtimg.cn/q=fx_susdchkd"
        r = requests.get(url, timeout=5)
        content = r.content.decode('gbk', errors='ignore')
        fields = content.split('~')
        if len(fields) > 7:
            # fields[7] 是当前价格
            rate_str = fields[7].strip()
            if rate_str and float(rate_str) > 0:
                rate = float(rate_str)
                print(f"[腾讯API] USD/HKD 汇率获取成功: {rate}")
                return round(rate, 4)
    except Exception as e:
        print(f"[腾讯API汇率获取失败] {e}")
    return None


def get_exchange_rate():
    """获取 USD/HKD 汇率，yfinance 优先，腾讯 API 备用"""
    global exchange_rates
    try:
        # 使用 yfinance 获取汇率
        ticker = yf.Ticker("USDHKD=X")
        hist = ticker.history(period="1d")
        if not hist.empty:
            exchange_rates['USD_HKD'] = round(float(hist['Close'].iloc[-1]), 4)
            exchange_rates['last_update'] = datetime.now().isoformat()
            print(f"[汇率更新] USD/HKD = {exchange_rates['USD_HKD']}")
            return
    except Exception as e:
        print(f"[yfinance汇率获取失败] {e}")

    # yfinance 失败，尝试腾讯 API
    print("[备用数据源] yfinance 汇率获取失败，尝试腾讯 API...")
    rate = get_exchange_rate_from_tencent()
    if rate:
        exchange_rates['USD_HKD'] = rate
        exchange_rates['last_update'] = datetime.now().isoformat()
        print(f"[汇率更新] USD/HKD = {exchange_rates['USD_HKD']}（来源：腾讯API）")
    else:
        print(f"[汇率获取失败] 所有数据源均失败，使用默认汇率 {exchange_rates['USD_HKD']}")


def get_stock_price(code, market):
    """获取单只股票的实时价格（原始货币），yfinance 优先，失败回退腾讯 API"""
    symbol = get_yfinance_symbol(code, market)
    try:
        ticker = yf.Ticker(symbol)
        # 尝试获取最新价格
        info = ticker.fast_info
        price = info.last_price
        if price and price > 0:
            return round(float(price), 4)
        # 备用方案：获取最近历史数据
        hist = ticker.history(period="1d")
        if not hist.empty:
            return round(float(hist['Close'].iloc[-1]), 4)
    except Exception as e:
        print(f"[yfinance价格获取失败] {symbol}: {e}")

    # yfinance 失败，尝试腾讯 API
    print(f"[备用数据源] {symbol} yfinance 失败，尝试腾讯 API...")
    tencent_price = get_stock_price_from_tencent(code, market)
    if tencent_price:
        return tencent_price

    return None


def get_stock_name_from_tencent(code, market):
    """通过腾讯股票 API 获取中文名称"""
    try:
        if market == 'HK':
            # 港股：hk + 补齐5位代码，如 hk03690
            padded = code.zfill(5)
            symbol = f"hk{padded}"
        elif market == 'US':
            # 美股：us + 代码，如 usAAPL
            symbol = f"us{code}"
        else:
            return ''

        url = f"https://qt.gtimg.cn/q={symbol}"
        r = requests.get(url, timeout=5)
        content = r.content.decode('gbk', errors='ignore')
        fields = content.split('~')
        if len(fields) > 1 and fields[1].strip():
            return fields[1].strip()
    except Exception as e:
        print(f"[腾讯API获取名称失败] {code}: {e}")
    return ''


def get_stock_price_from_tencent(code, market):
    """通过腾讯股票 API 获取实时价格（备用数据源）"""
    try:
        if market == 'HK':
            padded = code.zfill(5)
            symbol = f"hk{padded}"
        elif market == 'US':
            symbol = f"us{code}"
        else:
            return None

        url = f"https://qt.gtimg.cn/q={symbol}"
        r = requests.get(url, timeout=5)
        content = r.content.decode('gbk', errors='ignore')
        fields = content.split('~')
        if len(fields) > 3:
            # 腾讯 API 字段：fields[3] 是当前价格
            price_str = fields[3].strip()
            if price_str and float(price_str) > 0:
                price = float(price_str)
                print(f"[腾讯API] {code} 获取价格成功: {price}")
                return round(price, 4)
    except Exception as e:
        print(f"[腾讯API获取价格失败] {code}: {e}")
    return None


def get_stock_info(code, market):
    """获取股票名称和当前价格"""
    result = {'name': '', 'price': None}

    # 优先用腾讯 API 获取中文名称
    cn_name = get_stock_name_from_tencent(code, market)
    if cn_name:
        result['name'] = cn_name

    # 用 yfinance 获取价格（和英文名作为后备）
    symbol = get_yfinance_symbol(code, market)
    try:
        ticker = yf.Ticker(symbol)
        if not result['name']:
            info = ticker.info
            result['name'] = info.get('shortName', '') or info.get('longName', '') or ''
        # 获取价格
        try:
            fast = ticker.fast_info
            price = fast.last_price
            if price and price > 0:
                result['price'] = round(float(price), 4)
        except Exception:
            hist = ticker.history(period="1d")
            if not hist.empty:
                result['price'] = round(float(hist['Close'].iloc[-1]), 4)
    except Exception as e:
        print(f"[股票信息获取失败] {symbol}: {e}")
    return result


def convert_to_hkd(price, market):
    """将价格转换为港币"""
    if market == 'HK':
        return price
    elif market == 'US':
        return round(price * exchange_rates['USD_HKD'], 4)
    return price


def fetch_all_prices(stocks):
    """批量获取所有股票价格"""
    cache = load_price_cache()
    updated = False

    # 构建所有需要查询的 symbol
    symbols = []
    symbol_map = {}  # symbol -> stock info
    for stock in stocks:
        symbol = get_yfinance_symbol(stock['code'], stock['market'])
        symbols.append(symbol)
        symbol_map[symbol] = stock

    if not symbols:
        return cache

    # 记录 yfinance 获取失败的股票
    failed_symbols = list(symbols)

    try:
        # 批量下载
        tickers = yf.Tickers(' '.join(symbols))
        for symbol in symbols:
            try:
                ticker = tickers.tickers.get(symbol)
                if ticker:
                    info = ticker.fast_info
                    price = info.last_price if hasattr(info, 'last_price') else None
                    if price and price > 0:
                        cache[symbol] = {
                            'price': round(float(price), 4),
                            'time': datetime.now().isoformat()
                        }
                        updated = True
                        failed_symbols.remove(symbol)
            except Exception as e:
                print(f"[批量获取] {symbol} 失败: {e}")
    except Exception as e:
        print(f"[批量下载失败] {e}")

    # 对 yfinance 获取失败的股票，使用腾讯 API 作为备用数据源
    if failed_symbols:
        print(f"[备用数据源] 以下股票 yfinance 获取失败，尝试腾讯 API: {failed_symbols}")
        for symbol in failed_symbols:
            stock = symbol_map.get(symbol)
            if stock:
                price = get_stock_price_from_tencent(stock['code'], stock['market'])
                if price:
                    cache[symbol] = {
                        'price': price,
                        'time': datetime.now().isoformat()
                    }
                    updated = True

    if updated:
        save_price_cache(cache)

    return cache


@app.route('/')
def index():
    """返回前端页面"""
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/admin')
def admin():
    """返回后台管理页面"""
    return send_from_directory(app.static_folder, 'admin.html')


@app.route('/api/stocks', methods=['GET'])
def get_stocks():
    """获取所有股票持仓"""
    stocks = load_stocks()
    price_cache = load_price_cache()

    # 计算盈利和持仓占比（全部基于港币）
    total_value = 0
    for stock in stocks:
        market = stock.get('market', 'HK')
        current_hkd = convert_to_hkd(stock['current_price'], market)
        buy_hkd = convert_to_hkd(stock['buy_price'], market)
        stock['current_price_hkd'] = round(current_hkd, 2)
        stock['buy_price_hkd'] = round(buy_hkd, 2)
        total_value += current_hkd * stock['quantity']

    for stock in stocks:
        market_value = stock['current_price_hkd'] * stock['quantity']
        cost_value = stock['buy_price_hkd'] * stock['quantity']
        stock['cost_value_hkd'] = round(cost_value, 2)
        stock['profit'] = round(market_value - cost_value, 2)
        stock['profit_percent'] = round((market_value - cost_value) / cost_value * 100, 2) if cost_value > 0 else 0
        stock['position_ratio'] = round(market_value / total_value * 100, 2) if total_value > 0 else 0
        stock['market_value_hkd'] = round(market_value, 2)

        # 附带每只股票的价格更新时间
        symbol = get_yfinance_symbol(stock['code'], stock.get('market', 'HK'))
        if symbol in price_cache:
            stock['price_update_time'] = price_cache[symbol].get('time')
        else:
            stock['price_update_time'] = None

    # 计算板块统计
    sectors = {}
    for stock in stocks:
        t = stock.get('type', '其他')
        market_value_hkd = stock['market_value_hkd']
        if t not in sectors:
            sectors[t] = {
                'type': t,
                'market_value_hkd': 0,
                'count': 0
            }
        sectors[t]['market_value_hkd'] += market_value_hkd
        sectors[t]['count'] += 1

    sector_list = []
    for s in sectors.values():
        s['market_value_hkd'] = round(s['market_value_hkd'], 2)
        s['ratio'] = round(s['market_value_hkd'] / total_value * 100, 2) if total_value > 0 else 0
        sector_list.append(s)
    sector_list.sort(key=lambda x: x['market_value_hkd'], reverse=True)

    return jsonify({
        'stocks': stocks,
        'sectors': sector_list,
        'exchange_rates': {
            'USD_HKD': exchange_rates['USD_HKD'],
            'last_update': exchange_rates['last_update']
        },
        'last_price_update': get_last_price_update()
    })


@app.route('/api/stock-info', methods=['GET'])
def query_stock_info():
    """根据代码和市场查询股票名称和价格"""
    code = request.args.get('code', '').strip().upper()
    market = request.args.get('market', 'HK').strip().upper()
    if not code:
        return jsonify({'error': '请提供股票代码'}), 400

    info = get_stock_info(code, market)
    return jsonify({
        'code': code,
        'market': market,
        'name': info['name'],
        'price': info['price']
    })


@app.route('/api/stocks', methods=['POST'])
def add_stock():
    """添加股票"""
    data = request.json
    stocks = load_stocks()

    market = data.get('market', 'HK').upper()

    stock = {
        'id': max([s['id'] for s in stocks], default=0) + 1,
        'code': data['code'].upper(),
        'name': data['name'],
        'market': market,
        'type': data.get('type', '其他'),
        'buy_price': float(data['buy_price']),
        'quantity': float(data['quantity']),
        'current_price': float(data.get('current_price', data['buy_price']))
    }
    stocks.append(stock)
    save_stocks(stocks)
    return jsonify({'message': '添加成功', 'stock': stock}), 201


@app.route('/api/stocks/<int:stock_id>', methods=['PUT'])
def update_stock(stock_id):
    """更新股票信息"""
    data = request.json
    stocks = load_stocks()

    for stock in stocks:
        if stock['id'] == stock_id:
            stock['code'] = data.get('code', stock['code']).upper()
            stock['name'] = data.get('name', stock['name'])
            stock['market'] = data.get('market', stock.get('market', 'HK')).upper()
            stock['type'] = data.get('type', stock.get('type', '其他'))
            stock['buy_price'] = float(data.get('buy_price', stock['buy_price']))
            stock['quantity'] = float(data.get('quantity', stock['quantity']))
            stock['current_price'] = float(data.get('current_price', stock['current_price']))
            save_stocks(stocks)
            return jsonify({'message': '更新成功', 'stock': stock})

    return jsonify({'message': '未找到该股票'}), 404


@app.route('/api/stocks/<int:stock_id>', methods=['DELETE'])
def delete_stock(stock_id):
    """删除股票"""
    stocks = load_stocks()
    stocks = [s for s in stocks if s['id'] != stock_id]
    save_stocks(stocks)
    return jsonify({'message': '删除成功'})


@app.route('/api/refresh-prices', methods=['POST'])
def refresh_prices():
    """刷新所有股票实时价格"""
    stocks = load_stocks()
    if not stocks:
        return jsonify({'message': '没有持仓数据'})

    # 先更新汇率
    get_exchange_rate()

    # 获取所有价格
    cache = fetch_all_prices(stocks)

    # 更新股票的当前价格
    updated_count = 0
    for stock in stocks:
        symbol = get_yfinance_symbol(stock['code'], stock.get('market', 'HK'))
        if symbol in cache:
            stock['current_price'] = cache[symbol]['price']
            updated_count += 1

    save_stocks(stocks)
    timestamp = datetime.now().isoformat()
    set_last_price_update(timestamp)

    return jsonify({
        'message': f'价格刷新完成，更新了 {updated_count}/{len(stocks)} 只股票',
        'exchange_rates': {
            'USD_HKD': exchange_rates['USD_HKD'],
            'last_update': exchange_rates['last_update']
        },
        'last_price_update': timestamp
    })


@app.route('/api/refresh-exchange-rate', methods=['POST'])
def refresh_exchange_rate():
    """刷新汇率"""
    get_exchange_rate()
    return jsonify({
        'USD_HKD': exchange_rates['USD_HKD'],
        'last_update': exchange_rates['last_update']
    })


@app.route('/api/stocks/batch-update-price', methods=['POST'])
def batch_update_price():
    """批量手动更新当前价格"""
    data = request.json  # [{'id': 1, 'current_price': 10.5}, ...]
    stocks = load_stocks()

    for update in data:
        for stock in stocks:
            if stock['id'] == update['id']:
                stock['current_price'] = float(update['current_price'])
                break

    save_stocks(stocks)
    return jsonify({'message': '批量更新成功'})


def do_daily_refresh():
    """执行每日价格刷新"""
    stocks = load_stocks()
    if not stocks:
        print("[每日刷新] 没有持仓数据，跳过")
        return

    print(f"[每日刷新] 开始刷新 {len(stocks)} 只股票的价格...")
    get_exchange_rate()
    cache = fetch_all_prices(stocks)

    updated_count = 0
    for stock in stocks:
        symbol = get_yfinance_symbol(stock['code'], stock.get('market', 'HK'))
        if symbol in cache:
            stock['current_price'] = cache[symbol]['price']
            updated_count += 1

    save_stocks(stocks)
    timestamp = datetime.now().isoformat()
    set_last_price_update(timestamp)
    print(f"[每日刷新] 完成，更新了 {updated_count}/{len(stocks)} 只股票，时间: {timestamp}")


def auto_refresh_daily():
    """每日自动刷新线程"""
    # 启动时先刷新一次
    time.sleep(5)  # 等待服务启动
    do_daily_refresh()

    # 之后每24小时刷新一次
    while True:
        time.sleep(24 * 60 * 60)  # 24小时
        do_daily_refresh()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='股票持仓管理系统')
    parser.add_argument('-p', '--port', type=int, default=5000, help='服务端口号 (默认: 5000)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='监听地址 (默认: 0.0.0.0)')
    parser.add_argument('--no-debug', action='store_true', help='关闭调试模式')
    args = parser.parse_args()

    ensure_data_file()
    # 启动时获取汇率
    get_exchange_rate()

    debug_mode = not args.no_debug

    # 仅在主进程中启动每日自动刷新线程（避免 debug reloader 重复启动）
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not debug_mode:
        refresh_thread = threading.Thread(target=auto_refresh_daily, daemon=True)
        refresh_thread.start()

    print("=" * 50)
    print("  股票持仓管理系统")
    print(f"  当前汇率 USD/HKD = {exchange_rates['USD_HKD']}")
    print("  价格刷新频率: 每天自动更新一次")
    print(f"  前台查看: http://localhost:{args.port}")
    print(f"  后台管理: http://localhost:{args.port}/admin")
    print("=" * 50)
    app.run(debug=debug_mode, host=args.host, port=args.port)
