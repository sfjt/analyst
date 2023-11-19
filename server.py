from flask import Flask, render_template, Response, request, send_from_directory
from flask_pymongo import PyMongo, ASCENDING, DESCENDING
from pandas import DataFrame
from operator import itemgetter

from analyst.helpers import mongo_uri
from analyst.algo.plot import simple_plot
from jinja2.exceptions import UndefinedError

app = Flask(__name__)
app.config["MONGO_URI"] = mongo_uri()
mongo = PyMongo(app)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/screener", methods=["GET"])
def screener_tasks_list():
    default_limit = 100
    limit = request.args.get("limit", default_limit)

    screener_filter = {"taskType": "screener"}
    sort_conditions = [("started", DESCENDING)]
    cursor = mongo.db.tasks.find(screener_filter).sort(sort_conditions)
    screener_tasks = []
    for t in cursor.limit(limit):
        screener_tasks.append(t)
    cursor.close()

    get_stock_data_filter = {
        "taskType": "get_stock_data",
        "complete": True,
    }
    get_stock_data_task = mongo.db.tasks.find_one(
        get_stock_data_filter, sort=sort_conditions
    )

    return render_template(
        "screener_tasks_list.html",
        screener_tasks=screener_tasks,
        get_stock_data_task=get_stock_data_task,
    )


@app.route("/screener/<task_id>/<page>", methods=["GET"])
def screener_result_list(task_id, page):
    num_per_page = 5
    current_page_index = int(page)
    num_displayed = (current_page_index - 1) * num_per_page

    screener_filter = {"taskId": task_id}
    screener_result = mongo.db.screener_results.find_one(screener_filter)
    symbols = screener_result["tickerSymbols"]

    stock_data_filter = {"symbol.symbol": {"$in": symbols}}
    sort_condition = [("symbol.symbol", ASCENDING)]
    stock_data_cursor = mongo.db.stock_data.find(stock_data_filter).sort(sort_condition)
    num_total = mongo.db.stock_data.count_documents(stock_data_filter)

    next_page_index = None
    if num_total > (num_displayed + num_per_page):
        next_page_index = current_page_index + 1
    prev_page_index = None
    if current_page_index > 0:
        prev_page_index = current_page_index - 1
    pagination = {
        "next": next_page_index,
        "prev": prev_page_index,
        "total": num_total,
        "current": f"{num_displayed + 1} - {num_displayed + num_per_page}",
    }

    data = []
    num_quarters = 4
    for s in stock_data_cursor.skip(num_displayed).limit(num_per_page):
        q_financials = s["data"]["financial_statements"]["quarter"]
        q_financials = sorted(q_financials, key=itemgetter("date"), reverse=True)
        q_financials = q_financials[0:num_quarters]
        data.append(
            {
                "symbol": s["symbol"]["symbol"],
                "financials": q_financials,
            }
        )

    return render_template(
        "screener_stock_data.html",
        data=data,
        pagination=pagination,
        task_id=task_id,
    )


@app.route("/chart/simple/<symbol>", methods=["GET"])
def simple_candlestick_chart(symbol):
    default_days = 100
    days = request.args.get("days", default_days)
    default_w = 8
    w = request.args.get("w", default_w)
    default_h = 5
    h = request.args.get("h", default_h)

    ticker = mongo.db.stock_data.find_one({"symbol.symbol": symbol})
    prices = ticker["data"]["prices"]["historical"]
    df_prices = DataFrame.from_dict(prices)
    chart_image = simple_plot(df_prices, days, w, h)

    return Response(chart_image, content_type="image/jpeg")


@app.route("/scripts/<path:filename>")
def scripts(filename):
    return send_from_directory("./client/builds", filename)


@app.context_processor
def format_pct():
    def fn(pct: any):
        if not type(pct) is float:
            return pct
        return round(pct * 100, 2)

    return dict(format_pct=fn)


@app.context_processor
def format_num():
    def fn(n: any):
        is_int_or_float = type(n) is int or type(n) is float
        if not is_int_or_float:
            return n
        i = 0
        while abs(n) >= 1000:
            i += 1
            n /= 1000
        return "%.2f%s" % (n, ["", "K", "M", "G", "T", "P"][i])

    return dict(format_num=fn)


@app.context_processor
def fill_na():
    def fn(v: any):
        try:
            return v
        except UndefinedError:
            return None

    return dict(fill_na=fn)
