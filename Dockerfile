FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.21 /uv /bin/uv

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_NO_CACHE=1 \
    PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock .python-version README.md ./
RUN uv sync --locked --no-dev --no-install-project

COPY src ./src
COPY app.py ./
COPY app_pages ./app_pages
COPY .streamlit ./.streamlit
COPY data ./data
COPY models ./models
RUN uv sync --locked --no-dev

EXPOSE 8501

HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
