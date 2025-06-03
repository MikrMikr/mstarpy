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
                    fields: Optional[List[str]] = DFLT_FIELDS, 
                    securityType: Optional[str] = None, 
                    exchange: Optional[str] = None, 
                    universeIds: Optional[str] = None, 
                    pageSize: int = 10, 
                    currencyId: Optional[str] = None, 
                    filters: Optional[List[str]] = {}, 
                    proxies: Optional[Dict[str, str]] = {}) -> List[Dict[str, Any]]:
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

    if fields is not None:
        pass

    if securityType is not None:
        if securityType.lower() == "stock":
            params['filters'] = "|".join(prepare_filter(filters, FILTER_STOCK))
        elif securityType.lower() == "fund":
            params['filters'] = "|".join(prepare_filter(filters, FILTER_FUND))
        elif len(filters) > 0:
            print(f"Filter are not supported with security type {securityType} and will be ignored.")

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
            if exchange is not None and exchange is not "":
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
        print(f"0 securities found whith the term {term}")
    return securities



def prepare_filter(filters: List[str], valid_filters: List[str]) -> List[str]:
    filter_list = []
    # loop on filter dict
    for f in filters:
        if f not in valid_filters:
            print(
                f"""{f} is not a valid filter and will be ignored. You can find the
                possible filters with the method search_filter()."""
            )
        else:
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