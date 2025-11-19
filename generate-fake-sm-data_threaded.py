import concurrent.futures
import datetime
import json
import random
#from pybloomfilter import BloomFilter
from bloom_filter import BloomFilter
import string
from collections import deque
from google.cloud.storage import Client, transfer_manager
import os
import multiprocessing
from itertools import product  # Import product for efficient iteration
import copy
import threading
import orjson
from collections import deque
import argparse

# Cache for storing generated serial numbers
serial_cache = []
cache_filled = False

def generate_unique_serial_numbers(num_serials):
    """Generates a specified number of unique serial numbers."""
    global serial_cache
    global cache_filled

    if cache_filled:
        return serial_cache  # Return cached serials if available

    bf = BloomFilter(num_serials, 0.001)
    num_yielded = 0
    max_iterations = 10 * num_serials

    while num_yielded < num_serials and max_iterations > 0:
        new_int = random.randint(0, 31_000_000)  # 8 digits
        mac_address = f"MAC{new_int:08d}"

        if mac_address not in bf:
            bf.add(mac_address)
            num_yielded += 1
            max_iterations -= 1

            # Store the generated serial in the cache
            serial_cache.append(mac_address)

    cache_filled = True
    return serial_cache

# Generate Cartesian product of time components once
time_components = list(product(range(24), range(60), range(0, 60, 10)))

def write_fake_data_file(date, filename, file_path, tc):
    """Writes fake smart meter data to a JSON file."""
    # Use the pre-generated time_components
    #print(threading.current_thread().name +"-" + datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f") + " generating...")
    readings = [
        {"timestamp": datetime.datetime(date.year, date.month, date.day, *t).isoformat(),
         "reading": round(random.uniform(0.0, 0.9), 3)}
        for t in tc ]
    try:
        #json_readings = orjson.dumps(readings)
        with open(file_path, "wb") as outfile:
            for reading in readings:
                outfile.write(orjson.dumps(reading) + b"\n")
    except Exception as e:
        print(e)

    return filename


def generate_smart_meter_readings_for_day(storage_client, bucket_name, date_str, serial_numbers, q):
    """Generates readings for all meters on a single day and uploads them in a batch."""
    date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()

    # Create a temporary directory with date-specific subfolder
    temp_dir = f"/mnt/sm-disk/{date_str}"  # Subfolder inside 'temp'
    os.makedirs(temp_dir, exist_ok=True)

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=3000, thread_name_prefix="sm-demo-writer") 
    executor1 = concurrent.futures.ThreadPoolExecutor(max_workers=5, thread_name_prefix="sm-demo-uploaders") 
    # Generate JSON files for each meter
    #file_paths = []
    bucket = storage_client.bucket(bucket_name)
   
    try:
        for serial in serial_numbers:
            filename = f"{serial}.json"
            file_path = f"{temp_dir}/{filename}"
            futures = [executor.submit(write_fake_data_file, date, filename, file_path, copy.deepcopy(time_components))]
            #file_paths.append(filename)
            q.append(filename)

            #print(threading.current_thread().name + " qs: " + str(len(q)))
            if len(q) >= 25:
                print(threading.current_thread().name + ": got 25 to work with")
                #with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor1:
                file_paths = list(q)
                q.clear()
            
                executor1.submit(upload_file_batches, copy.copy(futures), bucket, date_str, copy.deepcopy(file_paths),temp_dir)
                futures.clear()            
                file_paths.clear()
                #print("files being uploaded & deleted...")
    except Exception as e:
        print(e)
            

def upload_file_batches(futures, bucket, date_str, file_paths, temp_dir):
    #print("uploading")
    #wait for all files to written completely
    for future in concurrent.futures.as_completed(futures):
        #print("got " + future.result())
        pass

    # Upload files using upload_many_from_filenames from transfer_manageri
    try:
        results = transfer_manager.upload_many_from_filenames(bucket, file_paths, source_directory=temp_dir, blob_name_prefix=f"dt={date_str}/", worker_type="thread", max_workers=100 )
        for name, result in zip(file_paths, results):
        # The results list is either `None` or an exception for each filename in
        # the input list, in order.
            if isinstance(result, Exception):
                print("Failed to upload {} due to exception: {}".format(name, result))
    
    except Exception as e:
            print(e)
    
    delete_uploaded_files(temp_dir, file_paths)
    
def delete_uploaded_files(temp_dir, file_paths):
    #print(threading.current_thread().name + ": deleting")
    # Clean up the temporary directory
    for filename in file_paths:
        os.remove(f"{temp_dir}/{filename}")

def generate_smart_meter_readings(bucket_name, serial_numbers, start_date_str, end_date_str):
    """Generates smart meter readings using multithreading and batch uploads to GCS."""
    num_cores = multiprocessing.cpu_count()
    max_threads = num_cores * 10  # Adjust if needed

    start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
    total_days = (end_date - start_date).days + 1

    storage_client = Client()
    # Split serial numbers into chunks
    serial_chunks = [serial_numbers[i::(8)] for i in range((8))]

    #executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_threads, thread_name_prefix="Generator-") 

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads, thread_name_prefix="sm-fake") as executor:
        for date in [start_date + datetime.timedelta(days=x) for x in range(total_days)]:
            date_str = date.strftime("%Y-%m-%d")
            for chunk in serial_chunks:
                futures = [executor.submit(
                    generate_smart_meter_readings_for_day,
                    storage_client,
                    bucket_name,
                    date_str,
                    chunk,
                    deque()
                    )]

    # Wait for all futures to complete before exiting the 'with' block
    for future in concurrent.futures.as_completed(futures):
        pass  # Or handle results if needed


# Get input
#bucket_name = "smart-meter-fake-data-1" 

#start_date_str = input("Enter start date (YYYY-MM-DD): ")
#end_date_str = input("Enter end date (YYYY-MM-DD): ")



def main():
    parser = argparse.ArgumentParser(description="Fake smart meter data generator")

    # Add arguments (customize these based on your needs)
    parser.add_argument("--start", type=str, help="Start Date (YYYY-MM-DD)", required=True)
    parser.add_argument("--end", type=str, help="End Date (YYYY-MM-DD)", required=True)
    parser.add_argument("--bucket", type=str, help="GCS bucket name", default="smart-meter-fake-data-t")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()  # Parse the command-line arguments
    start_date_str = args.start
    end_date_str = args.end
    bucket_name = args.bucket
    #num_serials = 30_000_000  # Or get it from user inpu
    num_serials = 1000000  # Or get it from user input
    #num_serials = 10  # Or get it from user input
    serial_numbers = generate_unique_serial_numbers(num_serials)

    # Generate readings and upload to GCS
    try:
        generate_smart_meter_readings(bucket_name, serial_numbers, start_date_str, end_date_str)
    except Exception as e:
        print(e)

if __name__ == "__main__":
    main()




