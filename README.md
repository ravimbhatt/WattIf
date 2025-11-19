# ⚡ WattIf: High-Scale Smart Meter Data Generator

**WattIf** is a high-performance Python utility designed to generate massive volumes of synthetic IoT (Smart Meter) time-series data and upload it directly to Google Cloud Storage (GCS).

It is engineered for stress-testing big data pipelines, data lakes, and cloud storage ingestion limits. It utilizes multi-threading, fast JSON serialization (`orjson`), and the GCS Transfer Manager to maximize throughput.

## 🚀 Features

  * **High Performance:** Uses `orjson` for extremely fast JSON serialization (replacing standard `json`).
  * **Memory Efficient:** Implements **Bloom Filters** to manage uniqueness for millions of generated Serial Numbers without high memory overhead.
  * **Parallel Ingestion:** Uses `concurrent.futures` to separate data generation (CPU/Disk bound) from data uploading (Network bound).
  * **GCS Transfer Manager:** Leverages the Google Cloud SDK's optimized transfer manager for parallel multi-part uploads.
  * **Pre-calculated Time Components:** Uses `itertools` to pre-compute timestamps, reducing CPU cycles inside the generation loop.

## 📋 Prerequisites

  * Python 3.8+
  * Google Cloud SDK installed and authenticated (`gcloud auth application-default login`).
  * A high-speed local disk (SSD recommended) mounted at `/mnt/sm-disk/` (or updated in the code) to handle temporary file I/O.

## 🛠️ Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/yourusername/wattif.git
    cd wattif
    ```

2.  **Install dependencies:**

    ```bash
    pip install google-cloud-storage bloom-filter orjson argparse
    ```

## 💻 Usage

Run the script from the command line using the required arguments.

```bash
python generator.py --start YYYY-MM-DD --end YYYY-MM-DD [OPTIONS]
```

### Arguments

| Flag | Description | Required | Default |
| :--- | :--- | :---: | :--- |
| `--start` | Start Date (format: `YYYY-MM-DD`) | ✅ | N/A |
| `--end` | End Date (format: `YYYY-MM-DD`) | ✅ | N/A |
| `--bucket` | Target GCS Bucket Name | No | `smart-meter-fake-data-t` |
| `-v`, `--verbose` | Enable verbose logging | No | `False` |

### Example

Generate data for the month of January 2024 and upload to `my-datalake-bucket`:

```bash
python generator.py --start 2024-01-01 --end 2024-01-31 --bucket my-datalake-bucket
```

## ⚙️ Configuration & Tuning

### Disk Path

The script is currently hardcoded to use a specific mount point for temporary storage to ensure high IOPs.

  * **Variable:** `temp_dir` in `generate_smart_meter_readings_for_day`
  * **Default:** `/mnt/sm-disk/`
  * **Tip:** Ensure this directory exists and has write permissions. If running locally on a laptop, change this to a relative path like `./temp_data`.

### Concurrency

You can tune the worker threads based on your machine's core count and I/O capabilities. Look for these variables in the code:

  * `write_executor`: Handles writing JSON to disk (I/O & CPU).
  * `upload_executor`: Handles pushing files to GCS (Network).
  * `transfer_manager ... max_workers`: Controls the GCS SDK internal thread pool.

## 🏗️ Architecture

The script operates in a Producer-Consumer pattern to ensure the disk doesn't fill up and the network stays saturated.

1.  **Initialization:** Generates N unique MAC addresses using a Bloom Filter to ensure uniqueness.
2.  **Time Loop:** Iterates through the requested date range day-by-day.
3.  **Generation (Producer):** \* Creates 24 hours of data (10-second intervals) for a batch of meters.
      * Writes NDJSON files to the local temp disk.
4.  **Upload (Consumer):**
      * Once a batch (e.g., 100 files) is written, a thread submits them to the GCS Transfer Manager.
      * Files are uploaded to `gs://BUCKET/dt=YYYY-MM-DD/`.
5.  **Cleanup:** Successfully uploaded files are immediately deleted from the local disk to free up space.

## ⚠️ Disclaimer

This tool generates **synthetic** data. The readings are randomized (`random.uniform`) and do not reflect actual electrical usage patterns. It is intended for infrastructure testing, not data science analysis.
