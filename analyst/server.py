from flask import Flask, render_template, Response, request
from flask_pymongo import PyMongo, ASCENDING, DESCENDING
from pandas import DataFrame

from .helpers import mongo_uri
from .web_api import GetStockDataTask
from .screener import ScreenerTask
from .algo.plot import simple_plot

app = Flask(__name__)
app.config["MONGO_URI"] = mongo_uri()
mongo = PyMongo(app)


def get_collection(collection_name: str):
    db_name = ScreenerTask.DB_NAME
    return mongo.cx[db_name][collection_name]


def get_task_collection():
    return get_collection(ScreenerTask.TASK_COLLECTION_NAME)


def get_stock_data_collection():
    return get_collection(ScreenerTask.STOCK_DATA_COLLECTION_NAME)


def get_screener_collection():
    return get_collection(ScreenerTask.SCREENER_COLLECTION_NAME)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/screener", methods=["GET"])
def screener_tasks_list():
    default_limit = 100
    limit = request.args.get("limit", default_limit)

    screener_filter = {"taskType": "screener"}
    sort_conditions = [("started", DESCENDING)]
    collection = get_task_collection()
    cursor = collection.find(screener_filter).sort(sort_conditions)
    screener_tasks = []
    for t in cursor.limit(limit):
        screener_tasks.append(t)
    cursor.close()

    get_stock_data_filter = {"taskType": "get_stock_data"}
    get_stock_data_task = collection.find_one(
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
    screener_collection = get_screener_collection()
    screener_result = screener_collection.find_one(screener_filter)
    symbols = screener_result["tickerSymbols"]

    stock_data_filter = {"symbol.symbol": {"$in": symbols}}
    sort_condition = [("symbol.symbol", ASCENDING)]
    stock_data_collection = get_stock_data_collection()
    stock_data_cursor = stock_data_collection.find(stock_data_filter).sort(
        sort_condition
    )
    num_total = get_stock_data_collection().count_documents(stock_data_filter)

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

    charts = []
    for s in stock_data_cursor.skip(num_displayed).limit(num_per_page):
        charts.append({"symbol": s["symbol"]["symbol"]})

    return render_template(
        "screener_stock_data.html",
        charts=charts,
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

    stock_data_collection = get_stock_data_collection()
    ticker = stock_data_collection.find_one({"symbol.symbol": symbol})
    prices = ticker["data"]["prices"]["historical"]
    df_prices = DataFrame.from_dict(prices)
    chart_image = simple_plot(df_prices, days, w, h)

    return Response(chart_image, content_type="image/jpeg")
