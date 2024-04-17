from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

def scrape_data_collection_ids_for_offset(base_url, offset):
    """
    Scrapes data collection IDs from a given page based on the offset.

    Args:
    - base_url (str): The base URL to scrape, excluding the offset query parameter.
    - offset (int): The offset to apply to the base URL for pagination.

    Returns:
    - List of data collection IDs for the given offset (list).
    """
    # Set up Chrome options for headless execution
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')

    # Set up Selenium WebDriver with headless Chrome
    driver = webdriver.Chrome(options=chrome_options)

    data_collection_ids = []

    # Construct the URL with the provided offset
    url = f"{base_url}{offset}"

    # Open the URL
    driver.get(url)

    # Wait for the dynamic content to load
    time.sleep(5)  # Adjust the sleep time if necessary

    # Find all elements with the specified class
    rows = driver.find_elements(By.CLASS_NAME, 'spms-row')

    # Extract data-collection-id from each row
    for row in rows:
        data_collection_ids.append(row.get_attribute('data-collection-id'))

    # Close the WebDriver
    driver.quit()

    return data_collection_ids

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import concurrent
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm.auto import tqdm
import pandas as pd
import time
import os

def setup_driver(headless=True):
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
    # service = Service(ChromeDriverManager().install())
    # driver = webdriver.Chrome(service=service, options=chrome_options)

    driver = webdriver.Chrome(options=chrome_options)
    return driver

def wait_for_element(driver, by_method, value, timeout=10, retry_interval=3, max_retries=5):
    retries = 0
    while retries < max_retries:
        try:
            return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by_method, value)))
        except TimeoutException:
            # print(f"Retry {retries+1}/{max_retries} for element {value} after timeout.")
            time.sleep(retry_interval)
            retries += 1
        finally:
            # print(f"Retry {retries+1}/{max_retries} for element {value} after timeout.")
            time.sleep(retry_interval)
    # raise TimeoutException(f"Element {value} not found after {max_retries} retries.")
    return "Missing Value or Timeout"  # Return None if element is not found

def fetch_data(collection_id):
    driver = setup_driver()
    try:
        print(f"Fetching data for collection: {collection_id}\n.")
        driver.get(f"https://www.cvh.ac.cn/spms/detail.php?id={collection_id}")

        # Fetch specific details as per your logic
        data = {
            'Collection ID': collection_id,
            'Image Link': wait_for_element(driver, By.ID, "spm_image", max_retries=5).get_attribute('src'),
            'Phylum (门)': wait_for_element(driver, By.ID, "taxon_phy_c", max_retries=5).text,
            'Order (目)': wait_for_element(driver, By.ID, "taxon_ord_c", max_retries=5).text,
            'Family (科)': wait_for_element(driver, By.ID, "taxon_fam_c", max_retries=5).text,
            'Genus (属)': wait_for_element(driver, By.ID, "taxon_gen_c", max_retries=5).text,
            'Scientific Name': wait_for_element(driver, By.ID, "formattedName", max_retries=5).text,
            'Chinese Name': wait_for_element(driver, By.ID, "chineseName", max_retries=5).text,
            'Identified By': wait_for_element(driver, By.ID, "identifiedBy", max_retries=5).text,
            'Date Identified': wait_for_element(driver, By.ID, "dateIdentified", max_retries=5).text,
            'Collector': wait_for_element(driver, By.ID, "recordedBy", max_retries=5).text,
            'Collection Number': wait_for_element(driver, By.ID, "recordNumber", max_retries=5).text,
            'Collection Date': wait_for_element(driver, By.ID, "verbatimEventDate", max_retries=5).text,
            'Collection Location': wait_for_element(driver, By.ID, "locality", max_retries=5).text,
            'Altitude': wait_for_element(driver, By.ID, "elevation", max_retries=5).text,
            'Habitat': wait_for_element(driver, By.ID, "habitat", max_retries=5).text,
            'Phenology': wait_for_element(driver, By.ID, "reproductiveCondition", max_retries=5).text
        }
        return data
    finally:
        driver.quit()

def fetch_collection_data_concurrently(path, collection_ids, max_workers=10):
    results = []

    # Initialize an empty DataFrame to hold column names. This is useful if you expect your first few calls might fail and return None.
    name = next((cid for cid in collection_ids if cid is not None), "default")

    # Concatenate path and name to form temp_path
    temp_path = f"{path}/{name}.csv"
    print(temp_path)

    # Ensure the directory exists before attempting to write to it
    os.makedirs(os.path.dirname(temp_path), exist_ok=True)

    pd.DataFrame(columns=['Collection ID', 'Image Link', 'Phylum (门)', 'Order (目)', 'Family (科)',
                          'Genus (属)', 'Scientific Name', 'Chinese Name', 'Identified By',
                          'Date Identified', 'Collector', 'Collection Number', 'Collection Date',
                          'Collection Location', 'Altitude', 'Habitat', 'Phenology']).to_csv(temp_path, mode='w', index=False, encoding='utf-8-sig')

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for cid in collection_ids:
            try:
                # Submitting the fetch_data function to the executor
                future = executor.submit(fetch_data, cid)
                futures.append(future)
            except Exception as submit_error:
                print(f"Failed to submit task for {cid}: {submit_error}")

        results = []
        for future in tqdm(as_completed(futures), total=len(collection_ids)):
            try:
                result = future.result()  # This will raise an exception if the task raised one
                if result:
                    # Attempt to append the result to the CSV file
                    try:
                        pd.DataFrame([result]).to_csv(temp_path, mode='a', header=False, index=False, encoding='utf-8-sig')
                    except PermissionError:
                        print(f"PermissionError: Unable to write to {temp_path}")
                    except Exception as write_error:
                        print(f"Error writing to file: {write_error}")
            except Exception as task_error:
                print(f"Error retrieving result from future: {task_error}")

    df = pd.DataFrame(results)
    return df


def scape_cvh(max_offset=298000, total_samples=300, sample_size=30, results_path=".", check_path="./last_offset.txt"):
    base_url = "https://www.cvh.ac.cn/spms/list.php?&offset="
    max_offset = max_offset
    # total_samples = 10000
    total_samples = total_samples
    sample_size = sample_size
    results_path = results_path
    check_path = check_path

    # Load or initialize offset
    if os.path.exists(check_path):
        with open(check_path, 'r') as file:
            offset = int(file.read().strip())
    else:
        offset = max_offset

    data_collection = []

    for _ in range(total_samples // sample_size):
        # Update and wrap-around offset using modulo
        offset = (offset - sample_size) % max_offset
        print(f"Fetching data from offset: {offset}")

        # Scrape and fetch data
        data_collection_ids = scrape_data_collection_ids_for_offset(base_url, offset)
        results = fetch_collection_data_concurrently(results_path, data_collection_ids, sample_size)
        data_collection.extend(results)

        # Save the current offset
        with open(check_path, 'w') as file:
            file.write(str(offset))

    # Convert list to DataFrame
    df = pd.DataFrame(data_collection)
    df.to_csv(results_path + "/results.csv", header=True, index=False, encoding='utf-8-sig')
    print("Data collection and saving completed.")
