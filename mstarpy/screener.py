import math
import requests
from typing import List, Dict, Any, Optional
from .utils import ASSET_TYPE, EXCHANGE, FIELDS, FILTER_FUND, FILTER_STOCK, SITE, DFLT_FIELDS, SCREENER_URL

from .stock import Stock
from .funds import Funds
from .security import Security
from .utils import random_user_agent
from .api import fetch_all_items_robust


def search_security(term: str, 
                    fields: Optional[List[str]] = [],  
                    exchange: Optional[str] = None, 
                    universeIds: Optional[str] = None, 
                    pageSize: int = 30, 
                    currencyId: Optional[str] = None, 
                    filters: Optional[dict[str, Any]] = {}, 
                    proxies: Optional[Dict[str, str]] = {}) -> List[Security]:
    """
    Search for securities based on specified criteria.
    
    This function searches for financial securities (stocks, bonds, funds, etc.) 
    matching the provided search term and optional filters. Returns a list of 
    securities with their associated metadata.

    Best results when searching for security ID with a universeId specified
    
    Args:
        term (str): The search term to query for securities. Can be a security 
            name, ticker symbol, ISIN, or other identifier.
        fields (Optional[List[str]], optional): List of specific data fields to 
            return for each security. If empty, returns default fields. 
            Examples: ['name', 'ticker', 'price', 'marketCap']. Defaults to ["SecId", 
            "TenforeId", "LegalName", "Universe", "ISIN", "ExchangeId", "ClosePrice", 
            "OngoingCharge", "Ticker", "fundShareClassId"].
        exchange (Optional[str], optional): Filter results by exchange code as defined in ISO 10383 MIC. 
            Examples: 'XNAS', 'XNYS', 'XLON'. Defaults to None (all exchanges).
        universeIds (Optional[str], optional): Pipe-separated string of universe 
            IDs to limit search scope. Used for filtering by specific investment 
            universes or indices. Defaults to None.
        pageSize (int, optional): Maximum number of results to return per page. 
            Must be between 1 and 100. Defaults to 10.
        currencyId (Optional[str], optional): (Does not work) Filter results by currency code. 
            Examples: 'USD', 'EUR', 'GBP'. Defaults to None (all currencies).
        filters (Optional[List[str]], optional): Additional filter criteria to 
            apply to the search. Format depends on API implementation. 
            Defaults to [].
        proxies (Optional[Dict[str, str]], optional): Proxy configuration for 
            HTTP requests. Format: {'http': 'proxy_url', 'https': 'proxy_url'}. 
            Defaults to {} (no proxy).
    
    Returns:
        List[Security]: A list of securities
    
    Raises:
        Nothing
    
    Examples:
        Basic search for Apple stock:
        >>> results = search_security("AAPL")
        >>> print(len(results))
        10
    """
    fields = list(set(fields + DFLT_FIELDS))
    params = {
        "page": 1,
        "pageSize": pageSize,
        "sortOrder": "LegalName asc",
        "outputType": "json",
        "version": 1,
        "securityDataPoints": "|".join(fields),
        "term": term,
        "filters": "",
    }

    params['filters'] = "|".join(prepare_filter(filters, FILTER_STOCK))

    if universeIds is not None:
        params['universeIds'] = universeIds

    if currencyId is not None:
        params['currencyId'] = universeIds

    # result = general_search(params, proxies=proxies)
    result = fetch_all_items_robust(SCREENER_URL, params, proxies)

    securities = []
    if len(result) > 0:
        for item in result:

            # Extra filter logic
            if exchange:
                if exchange not in item.get("ExchangeId",""):
                    continue
            
            if item["Universe"][:2] == "E0":
                exg = exchange if exchange is not None else ""
                security = Stock(term=None, params=item, proxies=proxies)
                securities.append(security)
            elif item["Universe"][:2] == "ET":
                security = Funds(term=None, params=item, proxies=proxies)
                securities.append(security)
            elif item["Universe"][:2] == "FO":
                security = Funds(term=None, params=item, proxies=proxies)
                securities.append(security)
            else:
                security = Security(term=None, params=item, proxies=proxies)
                securities.append(security)
            
    else:
        print(f"0 securities found for term {term}")
    return securities


def search_security_by_type(term: str,
                            securityType: str,
                            fields: Optional[List[str]] = [],  
                            exchange: Optional[str] = None,  
                            pageSize: int = 30, 
                            currencyId: Optional[str] = None, 
                            filters: Optional[dict[str, Any]] = {}, 
                            proxies: Optional[Dict[str, str]] = {}) -> List[Security]:
    KNOWN_UNIVERSES = {
        "funds": {
            "allexg":"FOGBR$$ALL|FOCHI$$ONS",
            "selectexg": "FOGBR$$ALL|FOCHI$$ONS"
        },
        "etf": {
            "allexg":"ETALL$$ALL",
            "selectexg": "ETEXG$"
        },
        "stock": {
            "allexg":"E0WWE$$ALL",
            "selectexg": "E0EXG$"
        },
        "trust": {
            "allexg":"CEWWE$$ALL",
            "selectexg": "CEEXG$"
        },
        "index": {
            "allexg":"IXMSX$$ALL",
            "selectexg": "IXMSX$$ALL"
        },
    }
    uId = ""
    try:
        uId = KNOWN_UNIVERSES[securityType.lower()]["allexg"]
        if exchange is not None and exchange.upper() != "ALL":
            uId = KNOWN_UNIVERSES[securityType.lower()]["selectexg"] + exchange.upper()
    except Exception as e:
        print(f"Unsupported value for securityType={securityType}. Supported values are: {[k for k in KNOWN_UNIVERSES]}")

    return search_security(term, fields=fields, exchange=None, universeIds=uId, pageSize=pageSize, currencyId=currencyId, filters=filters, proxies=proxies)


def prepare_filter(filters: Dict[str, Any], valid_filters: List[str]) -> List[str]:
    filter_list = []
    # loop on filter dict
    for f in filters:
        # if f not in valid_filters:
        #     print(
        #         f"""{f} is not a valid filter and will be ignored. You can find the
        #         possible filters with the method search_filter()."""
        #     )
        # else:
            # if list, IN condition
        if isinstance(filters[f], list):
            filter_list.append(f'{f}:IN:{":".join(filters[f])}')
        # if tuple, either, BTW, LT or GT condition
        elif isinstance(filters[f], tuple):
            if len(filters[f]) == 2:
                if isinstance(filters[f][0], (int, float)):
                    filter_list.append(f"{f}:BTW:{filters[f][0]}:{filters[f][1]}")
                elif filters[f][0] == "<":
                    filter_list.append(f"{f}:LT:{filters[f][1]}")
                elif filters[f][0] == ">":
                    filter_list.append(f"{f}:GT:{filters[f][1]}")
        # else IN condition
        else:
            filter_list.append(f"{f}:IN:{filters[f]}")
    return filter_list