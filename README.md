# analyst

A personal, experimental financial analysis tool.

## Quickstart

### Prerequisites

1. Have [Python](https://www.python.org/) ^3.11, [poetry](https://python-poetry.org/), and [docker](https://www.docker.com/) installed.
2. Get a [Financial Modeling Prep](https://site.financialmodelingprep.com/) API Key.

**(You may hit the rate limit if you use the free API key.)**

### Start a development environment

1. Rename `.env.example` to `.env` and specify these environment variables:
   - API_KEY: The key you got in the prerequisites step #2.
   - MONGO_ROOT_PASSWORD: Generate a password for the root user.
   - MONGO_ANALYST_PASSWORD: Generate a password for the analyst database user.
   - (Other environment variables: the preset values should work for local development/testing)
2. In the project root directory, run the commands below:
   ```shell
   poetry config virtualenvs.in-project true # To create venv in the project directory.
   poetry install
   poetry shell
   ./start_dev.sh # Chmod before executing script.
   ```
3. Run a CLI command defined in `analyst.__main__.py` to start a task.
4. Once the task is complete, open the local flask server to check results.
5. Run `docker compose down` to tear down.

## Usage

### Commands

(TBW)