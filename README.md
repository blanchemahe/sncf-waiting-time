# sncf-waiting-time
[![CI](https://github.com/blanchemahe/sncf-waiting-time/actions/workflows/ci.yml/badge.svg)](https://github.com/blanchemahe/sncf-waiting-time/actions/workflows/ci.yml)
Streamlit app exploring platform waiting-time deviations on the SNCF Transilien network (ENS Data Challenge), containerized with Docker.

## Requirements

The project uses [uv](https://docs.astral.sh/uv/) to manage Python and its dependencies.

```bash
uv sync
```

**On macOS**, the model relies on XGBoost, which needs the OpenMP runtime. It is a system library that uv cannot install, so install it once with [Homebrew](https://brew.sh/):

```bash
brew install libomp
```

This step is not needed with Docker: the image ships everything the app needs.
