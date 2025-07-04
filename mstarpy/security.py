import datetime
import re
import requests
import uuid
import time
import random

from .error import not_200_response
from .search import (search_funds, 
                     search_stock, 
                     token_chart
                     )
from .utils import (
    APIKEY,
    SITE,
    ASSET_TYPE, 
    EXCHANGE,
    random_user_agent
    )
from .api import request_with_retry
from typing import List, Dict, Any, Optional, Union


# with Universe field, we can detect the asset class
# done find all stock echange and create a search_equity method
# add parameter exchange to Security class and search stocks if stock and exchange

class Security:
    """
    Parent class to access data about security

    Args:
        term (str): text to find a fund can be a name, part of a name or the isin of the funds
        country (str) : text for code ISO 3166-1 alpha-2 of country, should be '' for etf
        exchange (str) : ISO 10383 code for exchange where the security is listed 
        pageSize (int): number of funds to return
        itemRange (int) : index of funds to return (must be inferior to PageSize)
        proxies = (dict) : set the proxy if needed , example : {"http": "http://host:port","https": "https://host:port"}
        params = (dict) : parameters to be used for manual object configuration

    Examples:
        >>> Security('0P0000712R', "ca", 9, 0)
        >>> Security('visa', "", 25, 2)

    Raises:
        TypeError: raised whenever the parameter type is not the type expected
        ValueError : raised whenever the parameter is not valid or no fund found

    """

    def __init__(
        self,
        term=None,
        asset_type: str = "",
        country: str = "",
        exchange: str = "",
        pageSize: int = 1,
        itemRange: int = 0,
        filters: dict = {},
        proxies: dict = {},
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not isinstance(asset_type, str):
            raise TypeError("asset_type parameter should be a string")

        if not isinstance(country, str):
            raise TypeError("country parameter should be a string")

        if country and not country.lower() in SITE.keys():
            raise ValueError(
                f'country parameter can only take one of the values: {", ".join(SITE.keys())}'
            )

        if not isinstance(exchange, str):
            raise TypeError("exchange parameter should be a string")
    
        if exchange and not exchange.upper() in EXCHANGE.keys():
            raise ValueError(
                f'Exchange parameter can only take one of the values: {", ".join(EXCHANGE.keys())}'
            )
        
        if not isinstance(pageSize, int):
            raise TypeError("pageSize parameter should be an integer")

        if not isinstance(itemRange, int):
            raise TypeError("itemRange parameter should be an integer")

        if pageSize <= itemRange:
            raise ValueError(
                "itemRange parameter should be strictly inferior to pageSize parameter"
            )

        if not isinstance(filters, dict):
            raise TypeError("filters parameter should be dict")

        if not isinstance(proxies, dict):
            raise TypeError("proxies parameter should be dict")

        self.proxies = proxies

        if country:
            self.site = SITE[country.lower()]["site"]
        else:
            self.site = ""

        self.country = country

        self.exchange = exchange

        self.asset_type = "security"

        code_list = []

        if term is None:
            self.__manual_configuration__(params)
            return # Exit early if search term was supplied to allow manual object initiation

        if exchange:
            code_list = search_stock(
                term,
                ["fundShareClassId", "SecId", "TenforeId", "LegalName", "Universe", "ISIN"],
                exchange=exchange,
                pageSize=pageSize,
                filters=filters,
                proxies=self.proxies,
            )
        else:
            code_list = search_funds(
                term,
                ["fundShareClassId", "SecId", "TenforeId", "LegalName", "Universe", "ISIN"],
                country,
                pageSize,
                filters=filters,
                proxies=self.proxies,
            )

        if code_list:
            if itemRange < len(code_list):
                self.code = code_list[itemRange]["fundShareClassId"]
                self.name = code_list[itemRange]["LegalName"]

                if "ISIN" in code_list[itemRange]:
                    self.isin = code_list[itemRange]["ISIN"]

                universe = code_list[itemRange]["Universe"]

                if universe[:2] == "E0":
                    self.asset_type = "stock"
                elif universe[:2] == "ET":
                    self.asset_type = "etf"
                elif universe[:2] == "FO":
                    self.asset_type = "fund"

                if universe[:2] == "E0" and asset_type in ["etf", "fund"]:
                    raise ValueError(
                        f"The security found with the term {term} is a stock and the parameter asset_type is equal to {asset_type}, the class Stock should be used with this security."
                    )

                if universe[:2] in ["FO", "ET"] and asset_type == "stock":
                    if universe[:2] == "FO":
                        raise ValueError(
                            f"The security found with the term {term} is a fund and the parameter asset_type is equal to {asset_type}, the class Fund should be used with this security."
                        )
                    else:
                        raise ValueError(
                            f"The security found with the term {term} is an ETF and the parameter asset_type is equal to {asset_type}, the class Fund should be used with this security."
                        )

            else:
                raise ValueError(
                    f"Found only {len(code_list)} {self.asset_type} with the term {term}. The paramater itemRange must maximum equal to {len(code_list)-1}"
                )
        else:
            if country:
                raise ValueError(
                    f"0 {self.asset_type} found with the term {term} and country {country}"
                )
            elif exchange:
                raise ValueError(
                    f"0 {self.asset_type} found with the term {term} and exchange {exchange}"
                )
            else:
                raise ValueError(f"0 {self.asset_type} found with the term {term}")


    def __manual_configuration__(self, params: Dict[str, Any]):
        try:
            self.code = params["fundShareClassId"]
            self.name = params["LegalName"]
            self.isin = params.get("ISIN", None)
            self.exchange = params.get("ExchangeId", None)
            self.asset_type = ASSET_TYPE.get(params["Universe"][:2], None)

            self.country = "gb" # TODO Not sure what is the best way to determine which API to use
            self.site = SITE[self.country.lower()]["site"]

            self.securityDataPoints = params # Save all params in case they are needed later

            # bearer_token = token_chart()
            # # url for nav
            # url = f"https://www.us-api.morningstar.com/md-api/proxy_request/data_point_service/v1/universes"
            # # header with bearer token
            # headers = {
            #     "user-agent": random_user_agent(),
            #     "authorization": f"Bearer {bearer_token}",
            #     "X-API-RequestId": str(uuid.uuid4()),
            #     "X-API-CorrelationId": str(uuid.uuid4()),
            #     "x-feed-id": str(uuid.uuid4()),
            #     "md-package-version": "1.11.0",
            #     "X-API-ComponentId": "analyticslab",
            #     "X-API-Sourceapp": "morningstar-data",
            #     "X-API-ProductId": "Direct",
            #     # "Content-Type": "application/json",
            # }
            # # response
            # response = requests.get(url, headers=headers, proxies=self.proxies)
            # import pdb; pdb.set_trace()
            # print(response.status_code)
            # print(response.text)
        except Exception as e:
            print(f"Error {e} when manually configuring security")

        

    def GetData(self, 
                field:str, 
                params:dict={}, 
                headers:dict={}, 
                url_suffix:str="data") -> dict|list:
        """
        Generic function to use MorningStar global api.

        Args:
            field (str) : endpoint of the request
            params (dict) : parameter for the request
            headers (dict) : headers of the request
            url_suffix (str) : suffixe of the url

        Raises:
            TypeError raised whenever type of paramater are invalid

        Returns:
            dict with data

        Examples:
            >>> Security("rmagx", "us").GetData("price/feeLevel")

        """

        if not isinstance(field, str):
            raise TypeError("field parameter should be a string")

        if not isinstance(params, dict):
            raise TypeError("params parameter should be a dict")

        if not isinstance(url_suffix, str):
            raise TypeError("url_suffix parameter should be a string")

        # url of API
        url = f"""https://api-global.morningstar.com/sal-service/v1/{self.asset_type}/{field}/{self.code}"""

        if url_suffix:
            url += f"""/{url_suffix}"""

        # headers
        default_headers = {
            "apikey": APIKEY,
        }

        all_headers = default_headers | headers

        response = request_with_retry("GET", url, headers=all_headers, proxies=self.proxies)
        # response = requests.get(
        #     url, params=params, headers=all_headers, proxies=self.proxies
        # )

        not_200_response(url, response)

        return response.json()

    def ltData(self, 
               field:str, 
               currency:str="EUR") -> dict:
        """
        Generic function to use MorningStar lt api.

        Args:
            field (str) : viewId in the params
            currency (str) : currency in 3 letters

        Raises:
            TypeError raised whenever type of paramater are invalid

        Returns:
            dict with data

        Examples:
            >>> Security("rmagx", "us").ltData("price/feeLevel")

        """
        if not isinstance(field, str):
            raise TypeError("field parameter should be a string")

        # url of API
        url = f"""https://lt.morningstar.com/api/rest.svc/klr5zyak8x/security_details/{self.code}"""

        params = {
            "viewId": field,
            "currencyId": currency,
            "itype": "msid",
            "languageId": "en",
            "responseViewFormat": "json",
        }
        response = requests.get(url, params=params, proxies=self.proxies)

        not_200_response(url, response)

        # responseis a list
        response_list = response.json()
        if response_list:
            return response_list[0]
        else:
            return {}

    def RealtimeData(self, 
                     url_suffix: str) -> dict:
        """
        This function retrieves historical data of the specified fields

        Args:
            url_suffix (str) : suffixe of the url

        Returns:
            dict of realtime data

        Examples:
            >>> Stock("visa", "us").RealtimeData("quotes")

        Raises:
            TypeError: raised whenever the parameter type 
            is not the type expected
            ConnectionError : raised whenever the response is not 200 OK

        """
        # error raised if url_suffix is not a string
        if not isinstance(url_suffix, str):
            raise TypeError("url_suffix parameter should be a string or a list")
        # url for realtime data
        url = f"""https://www.morningstar.com/api/v2/stores/realtime/{url_suffix}"""

        # header with user agent
        headers = {
                    'user-agent': random_user_agent(), 
                    }
        #parameters of the request
        params = {"securities": self.code}
        # response
        response = requests.get(url, 
                                params=params, 
                                headers=headers, 
                                proxies=self.proxies,
                                timeout=60)
        # manage response
        not_200_response(url, response)
        # result
        return response.json()
    
    def TimeSeries(self, 
                   field:str|list, 
                   start_date:datetime.datetime,
                   end_date:datetime.datetime,
                   frequency:str="daily") -> list:
        """
        This function retrieves historical data of the specified fields

        Args:
            field (str|list) : field to retrieve, can be a string or a list of string
            start_date (datetime) : start date to get history
            end_date (datetime) : end date to get history
            frequency (str) : can be daily, weekly, monthly

        Returns:
            list of dict time series

        Examples:
            >>> Funds("RMAGX", "us").TimeSeries(["nav","totalReturn"],datetime.datetime.today()- datetime.timedelta(30),datetime.datetime.today())

        Raises:
            TypeError: raised whenever the parameter type is not the type expected
            ValueError : raised whenever the parameter is not valid or no funds found

        """

        # error raised if field is not a string or a list
        if not isinstance(field, (str, list)):
            raise TypeError("field parameter should be a string or a list")

        # error raised if start_date is note a datetime.date
        if not isinstance(start_date, datetime.date):
            raise TypeError("start_date parameter should be a datetime.date")

        # error raised if end_date is note a datetime.date
        if not isinstance(end_date, datetime.date):
            raise TypeError("end_date parameter should be a datetime.date")

        # error if end_date < start_date
        if end_date < start_date:
            raise ValueError("end_date must be more recent than start_date")

        # error raised if frequency is not a string
        if not isinstance(frequency, str):
            raise TypeError("frequency parameter should be a string")

        # dict of frequency
        frequency_row = {"daily": "d", "weekly": "w", "monthly": "m"}

        # raise an error if frequency is not daily, wekly or monthly
        if frequency not in frequency_row:
            raise ValueError(
                f"frequency parameter must take one of the following value : { ', '.join(frequency_row.keys())}"
            )

        if isinstance(field, list):
            queryField = ",".join(field)
        else:
            queryField = field

        # bearer token
        bearer_token = token_chart()
        # url for nav
        url = "https://www.us-api.morningstar.com/QS-markets/chartservice/v2/timeseries"
        # header with bearer token
        headers = {
            "user-agent": random_user_agent(),
            "authorization": f"Bearer {bearer_token}",
        }
        #params of the request
        params ={
            "query" : f"{self.code}:{queryField}",
            "frequency": frequency_row[frequency],
            "startDate": start_date.strftime('%Y-%m-%d'),
            "endDate": end_date.strftime('%Y-%m-%d'),
            "trackMarketData": "3.6.3",
            "instid": "DOTCOM",
        }
        # response
        response = request_with_retry("GET", url,
                                    params=params,
                                    headers=headers, 
                                    proxies=self.proxies)
        # response = requests.get(url,
        #                         params=params,
        #                         headers=headers, 
        #                         proxies=self.proxies)
        # manage response
        not_200_response(url, response)
        # result
        result = response.json()
        # return empty list if we don't get data
        if not result:
            return []
        if "series" in result[0]:
            return result[0]["series"]

        return []

    