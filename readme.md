# Spotify Dump Top Tracks Exporter

A lightweight, multi-threaded GUI application built with Python to query large Spotify data dumps stored in DuckDB. It filters tracks by release year, identifies the **single most popular track per artist**, and exports the **top 11,000** results globally to a CSV file.

## 🎯 Core Features

- **Batch Processing:** Iterates through the database using alphanumeric prefixes (0-9, A-z) to handle large datasets without freezing the UI.
- **"One Track Per Artist" Logic:** Uses DuckDB's `arg_max` function to ensure that for every artist, only their specific track with the highest popularity score is selected.
- **Custom Filtering:** User-defined Start and End years (based on Album Release Date).
- **Pandas Post-Processing:** Performs a final in-memory sort to strictly cut the list to the top 11,000 most popular tracks globally within the selected era.
- **Performance:** Configured to utilize multi-threading (8 threads) and manages memory usage (capped at 12GB) for efficiency.

## 🛠 Prerequisites

### Python Dependencies
You need Python installed. This script relies on `duckdb` and `pandas`. `tkinter` is usually included with Python standard installations.

```bash
pip install duckdb pandas
