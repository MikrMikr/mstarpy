import math
import requests
import random
import time
from typing import List, Optional, Union
from .utils import random_user_agent

def fetch_all_items_robust(base_url: str, 
                          params: Optional[dict] = None,
                          proxies: Optional[dict] = None,
                          max_retries: int = 3,
                          timeout: int = 30) -> List[dict]:
    """
    Fetch all pages from multipage API response with retry logic and timeout handling.
    
    Args:
        base_url: The API endpoint URL
        params: Additional query parameters
        max_retries: Maximum number of retries per request
        timeout: Request timeout in seconds
        
    Returns:
        List of all items combined from all pages
    """
    all_items = []
    current_page = 1
    
    if params is None:
        params = {}
    
    headers = {
        "user-agent": random_user_agent(),
    }

    while True:
        request_params = params.copy()
        request_params['page'] = current_page
        
        response = request_with_retry(
                    "GET", 
                    base_url, 
                    params=request_params, 
                    timeout=timeout,
                    headers=headers,
                    proxies=proxies
        )
        # Retry logic
        # for attempt in range(max_retries + 1):
        #     try:
        #         response = requests.get(
        #             base_url, 
        #             params=request_params, 
        #             timeout=timeout,
        #             headers=headers,
        #             proxies=proxies
        #         )
        #         response.raise_for_status()
        #         break
                
        #     except requests.RequestException as e:
        #         if attempt == max_retries:
        #             raise
        #         print(f"Attempt {attempt + 1} failed, retrying: {e}")
                
        try:
            data = response.json()
            rows = data.get('rows', [])
            
            if not rows:  # Empty page
                break
                
            all_items.extend(rows)
            
            # Check if this is the last page
            total = data.get('total', 0)
            page_size = data.get('pageSize', len(rows))
            
            if page_size > 0:
                total_pages = math.ceil(total / page_size)
                if current_page >= total_pages:
                    break
            
            current_page += 1
            
        except (ValueError, TypeError) as e:
            print(f"Error parsing JSON from page {current_page}: {e}")
            raise
                
    return all_items

def request_with_retry(method: str, url: str, 
    headers: Optional[dict] = None, 
    verify: Optional[bool] = True, 
    max_retries: Optional[int] = 3,
    backoff_factor: Optional[float] = 1.0,
    timeout: Optional[int] = 30,
    data: Optional[Union[dict, str]] = None,
    params: Optional[dict] = None,
    proxies: Optional[dict] = None
) -> requests.Response:
    STATUS_FORCE_LIST = [500, 501, 502, 503, 504]
    MAX_REDIRECTS = 5
    REDIRECT_CODES = [301, 307]

    # timeout = 30
    # data = None
    # verify = True
    # params = None
    # max_retries = 3
    retry_count = 0
    while retry_count <= max_retries:
        try:
            res = requests.request(method, url, headers=headers, verify=verify, data=data, allow_redirects=False, params=params, proxies=proxies, timeout=timeout)

            redirect_count = 0

            while res.status_code in REDIRECT_CODES and redirect_count <= MAX_REDIRECTS:
                redirected_url = res.headers["Location"]
                print(f"Redirection to {redirected_url} for {method} request to {url}")

                res = requests.request(method, redirected_url, headers=headers, verify=verify, data=data, allow_redirects=False, params=params, proxies=proxies, timeout=timeout)

                redirect_count += 1

            res.raise_for_status()
            return res

        except (requests.RequestException, requests.Timeout, requests.ConnectionError) as e:
            retry_count += 1

            if retry_count > max_retries:
                print(f"All {max_retries} retries failed for {url}")
                raise e
            
            # Calculate exponential backoff delay
            delay = backoff_factor * (2 ** (retry_count - 1)) + random.uniform(0, 1)
            print(f"Request failed (attempt {retry_count}), retrying in {delay:.2f} seconds: {e}")
            time.sleep(delay)
    raise requests.RequestException(f"Failed to complete request after {max_retries} retries")