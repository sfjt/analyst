import argparse


# from .screener import screen
from .web_api import run_get_stock_data_task

parser = argparse.ArgumentParser(
    description="A personal financial analysis tool", prog="analyst"
)
subparsers = parser.add_subparsers()

# parser_screener = subparsers.add_parser("screener")
# parser_screener.set_defaults(fn=screen)

parser_get_stock_data = subparsers.add_parser("getstockdata")
parser_get_stock_data.set_defaults(fn=run_get_stock_data_task)

args = parser.parse_args()

if hasattr(args, "fn"):
    args.fn()
else:
    parser.print_help()
