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


def task_collection():
    db_name = ScreenerTask.DB_NAME
    collection_name = ScreenerTask.TASK_COLLECTION_NAME
    return mongo.cx[db_name][collection_name]


def stock_data_collection():
    db_name = ScreenerTask.DB_NAME
    collection_name = ScreenerTask.STOCK_DATA_COLLECTION_NAME
    return mongo.cx[db_name][collection_name]


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/screener", methods=["GET"])
def screener_tasks_list():
    default_limit = 100
    limit = request.args.get("limit", default_limit)
    task_cursor = task_collection().find().sort("started", DESCENDING)
    tasks = []
    for t in task_cursor.limit(limit):
        tasks.append(t)
    return render_template("screener_tasks_list.html", tasks=tasks)


@app.route("/screener/<task_id>/<page>")
def screener_result(task_id, page):
    num_per_page = 5
    current_page_index = int(page)
    num_displayed = (current_page_index - 1) * num_per_page

    stock_data_cursor = stock_data_collection().find({"taskId": task_id}).sort("symbol.symbol", ASCENDING)
    num_total = stock_data_collection().count_documents({"taskId": task_id})

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
        charts.append(
            {
                "symbol": s["symbol"]["symbol"]
            }
        )

    return render_template(
        "screener_stock_data.html", charts=charts, pagination=pagination, task_id=task_id
    )


@app.route("/chart/simple/<symbol>")
def simple_candlestick_chart(symbol):
    default_days = 100
    days = request.args.get("days", default_days)
    default_w = 8
    w = request.args.get("w", default_w)
    default_h = 5
    h = request.args.get("h", default_h)
    db_name = GetStockDataTask.DB_NAME
    collection_name = GetStockDataTask.STOCK_DATA_COLLECTION_NAME
    collection = mongo.cx[db_name][collection_name]
    ticker = collection.find_one({"symbol.symbol": symbol})
    prices = ticker["data"]["prices"]["historical"]
    df_prices = DataFrame.from_dict(prices)
    chart_image = simple_plot(df_prices, days, w, h)
    return Response(chart_image, content_type="image/jpeg")
