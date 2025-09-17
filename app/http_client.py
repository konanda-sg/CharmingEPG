import asyncio
from typing import Dict, Optional, Any
import aiohttp
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .config import Config
from .logger import get_logger

logger = get_logger(__name__)


class HTTPError(Exception):
    """Custom HTTP error for better error handling"""
    def __init__(self, status_code: int, message: str, url: str):
        self.status_code = status_code
        self.message = message
        self.url = url
        super().__init__(f"HTTP {status_code}: {message} (URL: {url})")


class HTTPClient:
    """Shared HTTP client with retry logic and proper error handling"""

    def __init__(self):
        self.timeout = Config.HTTP_TIMEOUT
        self.proxies = Config.get_proxies()
        self.default_headers = {
            "User-Agent": Config.DEFAULT_USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh-TW;q=0.9,zh;q=0.8,en-US;q=0.7,en;q=0.6",
            "Cache-Control": "no-cache",
        }

    @retry(
        stop=stop_after_attempt(Config.HTTP_MAX_RETRIES),
        wait=wait_exponential(multiplier=Config.HTTP_RETRY_BACKOFF),
        retry=retry_if_exception_type((requests.RequestException, HTTPError)),
        reraise=True
    )
    def get(self, url: str, headers: Optional[Dict[str, str]] = None,
            params: Optional[Dict[str, Any]] = None, **kwargs) -> requests.Response:
        """
        Synchronous GET request with retry logic

        Args:
            url: Request URL
            headers: Additional headers
            params: Query parameters
            **kwargs: Additional requests arguments

        Returns:
            requests.Response object

        Raises:
            HTTPError: For HTTP errors (4xx, 5xx)
            requests.RequestException: For connection errors
        """
        request_headers = self.default_headers.copy()
        if headers:
            request_headers.update(headers)

        try:
            logger.info(f"Making GET request to: {url}")

            response = requests.get(
                url,
                headers=request_headers,
                params=params,
                proxies=self.proxies,
                timeout=self.timeout,
                **kwargs
            )

            # Check for HTTP errors
            if not response.ok:
                raise HTTPError(
                    status_code=response.status_code,
                    message=response.reason or "Unknown error",
                    url=url
                )

            logger.debug(f"Successfully fetched: {url} (Status: {response.status_code})")
            return response

        except requests.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            raise
        except HTTPError as e:
            logger.error(f"HTTP error for {url}: {e}")
            raise

    @retry(
        stop=stop_after_attempt(Config.HTTP_MAX_RETRIES),
        wait=wait_exponential(multiplier=Config.HTTP_RETRY_BACKOFF),
        retry=retry_if_exception_type((aiohttp.ClientError, HTTPError)),
        reraise=True
    )
    async def async_get(self, url: str, headers: Optional[Dict[str, str]] = None,
                       params: Optional[Dict[str, Any]] = None, **kwargs) -> aiohttp.ClientResponse:
        """
        Asynchronous GET request with retry logic

        Args:
            url: Request URL
            headers: Additional headers
            params: Query parameters
            **kwargs: Additional aiohttp arguments

        Returns:
            aiohttp.ClientResponse object

        Raises:
            HTTPError: For HTTP errors (4xx, 5xx)
            aiohttp.ClientError: For connection errors
        """
        request_headers = self.default_headers.copy()
        if headers:
            request_headers.update(headers)

        connector_kwargs = {}
        if self.proxies:
            # Note: aiohttp proxy configuration differs from requests
            logger.debug(f"Using proxy: {self.proxies}")

        timeout = aiohttp.ClientTimeout(total=self.timeout)

        try:
            logger.info(f"Making async GET request to: {url}")

            async with aiohttp.ClientSession(
                timeout=timeout,
                headers=request_headers,
                **connector_kwargs
            ) as session:
                async with session.get(url, params=params, **kwargs) as response:
                    # Check for HTTP errors
                    if not response.ok:
                        raise HTTPError(
                            status_code=response.status,
                            message=response.reason or "Unknown error",
                            url=url
                        )

                    logger.debug(f"Successfully fetched: {url} (Status: {response.status})")
                    return response

        except aiohttp.ClientError as e:
            logger.error(f"Async request failed for {url}: {e}")
            raise
        except HTTPError as e:
            logger.error(f"HTTP error for {url}: {e}")
            raise

    def post(self, url: str, data: Optional[Any] = None, json: Optional[Dict] = None,
             headers: Optional[Dict[str, str]] = None, **kwargs) -> requests.Response:
        """Synchronous POST request with retry logic"""
        return self._request_with_retry("POST", url, data=data, json=json, headers=headers, **kwargs)

    async def async_post(self, url: str, data: Optional[Any] = None, json: Optional[Dict] = None,
                        headers: Optional[Dict[str, str]] = None, **kwargs) -> aiohttp.ClientResponse:
        """Asynchronous POST request with retry logic"""
        return await self._async_request_with_retry("POST", url, data=data, json=json, headers=headers, **kwargs)

    @retry(
        stop=stop_after_attempt(Config.HTTP_MAX_RETRIES),
        wait=wait_exponential(multiplier=Config.HTTP_RETRY_BACKOFF),
        retry=retry_if_exception_type((requests.RequestException, HTTPError)),
        reraise=True
    )
    def _request_with_retry(self, method: str, url: str, **kwargs) -> requests.Response:
        """Generic request method with retry logic"""
        request_headers = self.default_headers.copy()
        if kwargs.get('headers'):
            request_headers.update(kwargs.pop('headers'))

        try:
            logger.info(f"Making {method} request to: {url}")

            response = requests.request(
                method,
                url,
                headers=request_headers,
                proxies=self.proxies,
                timeout=self.timeout,
                **kwargs
            )

            if not response.ok:
                raise HTTPError(
                    status_code=response.status_code,
                    message=response.reason or "Unknown error",
                    url=url
                )

            logger.debug(f"Successfully completed {method} request: {url} (Status: {response.status_code})")
            return response

        except requests.RequestException as e:
            logger.error(f"{method} request failed for {url}: {e}")
            raise

    @retry(
        stop=stop_after_attempt(Config.HTTP_MAX_RETRIES),
        wait=wait_exponential(multiplier=Config.HTTP_RETRY_BACKOFF),
        retry=retry_if_exception_type((aiohttp.ClientError, HTTPError)),
        reraise=True
    )
    async def _async_request_with_retry(self, method: str, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Generic async request method with retry logic"""
        request_headers = self.default_headers.copy()
        if kwargs.get('headers'):
            request_headers.update(kwargs.pop('headers'))

        timeout = aiohttp.ClientTimeout(total=self.timeout)

        try:
            logger.info(f"Making async {method} request to: {url}")

            async with aiohttp.ClientSession(timeout=timeout, headers=request_headers) as session:
                async with session.request(method, url, **kwargs) as response:
                    if not response.ok:
                        raise HTTPError(
                            status_code=response.status,
                            message=response.reason or "Unknown error",
                            url=url
                        )

                    logger.debug(f"Successfully completed async {method} request: {url} (Status: {response.status})")
                    return response

        except aiohttp.ClientError as e:
            logger.error(f"Async {method} request failed for {url}: {e}")
            raise


# Global HTTP client instance
http_client = HTTPClient()


def get_http_client() -> HTTPClient:
    """Get the global HTTP client instance"""
    return http_client