# analyst

A personal, experimental financial analysis tool.

## Quickstart

### Prerequisites

1. Have [Python](https://www.python.org/) ^3.11, [poetry](https://python-poetry.org/), and [docker](https://www.docker.com/) installed.
2. Get a [polygon.io](https://polygon.io/) API Key.

(**Caveat:** You may hit the rate limit if you use the free API key.)

### Start a development environment

1. Rename `.env.example` to `.env` and specify these environment variables:
   - POLYGON_API_KEY: The key you got in the prerequisites step #2.
   - MONGO_HOST: Use `localhost` for local testing.
   - MONGO_PORT: Can be anything for local testing. `27017` is the well-known port for MongoDB.
   - MONGO_USERNAME: Can be anything for local testing. For example, `root`.
   - MONGO_PASSWORD: Generate a random password.
2. In the project root directory, run the commands below:
   ```shell
   poetry config virtualenvs.in-project true # To create venv in the project directory.
   poetry install
   poetry shell
   ./start_dev.sh # You may want to chmod before executing script.
   ```
3. Run a CLI command defined in `analyst.__main__.py`; for example `python -m analyst screener`
4. Open the local flask server with your browser to check results.
5. Run `docker compose down` to tear down.
