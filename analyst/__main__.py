import argparse


from .screener import screen


parser = argparse.ArgumentParser(
    description="A personal financial analysis tool", prog="analyst"
)
subparsers = parser.add_subparsers()

parser_screener = subparsers.add_parser("screener")
parser_screener.set_defaults(fn=screen)

args = parser.parse_args()

if hasattr(args, "fn"):
    args.fn()
else:
    parser.print_help()
