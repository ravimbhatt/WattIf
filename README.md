💡 WattIf: Smart Meter Data Generator & Anomaly Detection

WattIf is a comprehensive toolkit designed for the energy sector. It consists of a high-performance synthetic data generator and a sophisticated anomaly detection analysis pipeline using Google Cloud.

It is engineered to stress-test big data ingestion pipelines and demonstrate predictive maintenance capabilities using Google Cloud Dataplex.

🚀 Features
1. Data Generation (The "Watt")
High Performance: Uses orjson and multi-threading to generate massive volumes of synthetic smart meter JSON data.

Memory Efficient: Implements Bloom Filters to manage uniqueness for millions of serial numbers.

Parallel Ingestion: seamless upload to Google Cloud Storage (GCS) using the Transfer Manager.

2. Analysis & ML (The "If")
Automated Anomaly Detection: Includes a Jupyter notebook (Smart_Meter_Anomaly_Detection.ipynb) to set up Google Cloud Dataplex DataScans.

Predictive Insights: Uses AI models trained on historical BigQuery data to detect anomalies in meter readings.

Rule-Based Logic: configured to monitor key metrics (Average and Max consumption) on hourly rolled data (consumption_hour_rolled) with a 99% anomaly probability threshold.

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
    or
    ```bash
    pip install -r requirements.txt
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


Analyze Data (Anomaly Detection)
Once the data is loaded into BigQuery (e.g., via a GCS-to-BigQuery transfer job):
Open Smart_Meter_Anomaly_Detection.ipynb in Jupyter or Google Colab.
Update the project_id and bigquery_source_table_full_path variables.
Run the notebook to provision a Dataplex DataScan.
Metric: Checks consumption_hour_rolled.
Logic: Flags data points that deviate statistically from the trained baseline (AVG/MAX).
Output: Results are exported to a BigQuery table for visualization.


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

## ⚙️ Flow
Generator: Python script creates NDJSON files locally.

Ingest: Files are pushed to GCS in parallel batches.

Storage: Data is moved from GCS to BigQuery (External Table or Native Table).

Quality: Dataplex runs an Anomaly Detection scan on the BigQuery table.

Alerting: Anomalies (e.g., energy theft, meter malfunction) are flagged based on the 0.99 probability threshold defined in the notebook.

## ⚠️ Disclaimer

This tool generates **synthetic** data. The readings are randomized (`random.uniform`) and do not reflect actual electrical usage patterns. It is intended for infrastructure testing, not data science analysis.
