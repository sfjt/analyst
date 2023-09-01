from flask import Flask, render_template, Response
from flask_pymongo import PyMongo, ASCENDING, DESCENDING
from pandas import DataFrame

from .helpers import mongo_uri
from .screener import ScreenerTask
from .algo.example import simple_plot

app = Flask(__name__)
app.config["MONGO_URI"] = mongo_uri()
mongo = PyMongo(app)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/screener")
def screener_tasks():
    num_limit = 100
    db = mongo.cx[ScreenerTask.DB_NAME]
    collection = db[ScreenerTask.TASK_COLLECTION_NAME]
    task_cursor = collection.find().sort("started", DESCENDING)
    tasks = []
    for t in task_cursor.limit(num_limit):
        tasks.append(t)
    return render_template("screener_tasks.html", tasks=tasks)


@app.route("/screener/<task_id>/<page>")
def screener_result(task_id, page):
    num_limit = 5
    current_page_index = int(page)
    num_skip = (current_page_index - 1) * num_limit
    db = mongo.cx[ScreenerTask.DB_NAME]
    collection = db[ScreenerTask.TICKER_COLLECTION_NAME]
    ticker_cursor = collection.find({"task_id": task_id}).sort("ticker", ASCENDING)
    num_docs = collection.count_documents({"task_id": task_id})

    next_page_index = None
    if num_docs > (num_skip + num_limit):
        next_page_index = current_page_index + 1
    prev_page_index = None
    if current_page_index > 0:
        prev_page_index = current_page_index - 1
    pagination = {
        "next": next_page_index,
        "prev": prev_page_index,
        "total": num_docs,
        "current": f"{num_skip + 1} - {num_skip + num_limit}",
    }

    charts = []
    for t in ticker_cursor.skip(num_skip).limit(num_limit):
        charts.append(
            {
                "ticker": t["ticker"],
                "chart": simple_plot(DataFrame(t["data"])),
            }
        )

    return render_template(
        "screener_charts.html", charts=charts, pagination=pagination, task_id=task_id
    )


@app.route("/charts/simple/<task_id>/<ticker>")
def simple_candlestick_chart(task_id, ticker):
    db = mongo.cx[ScreenerTask.DB_NAME]
    collection = db[ScreenerTask.TICKER_COLLECTION_NAME]
    ticker = collection.find_one(
        {
            "task_id": task_id,
            "ticker": ticker,
        }
    )
    chart_image = simple_plot(DataFrame(ticker["data"]))
    return Response(chart_image, content_type="image/jpeg")
