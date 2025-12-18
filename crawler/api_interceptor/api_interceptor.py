from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from api_call_collector import ApiCallCollector
from lib.log import Logger

class APICallInterceptor(ABC):
    collectors: list[ApiCallCollector]
    logger: Logger

    @abstractmethod
    @asynccontextmanager
    async def intercept(self):
        """
        This async context manager intercepts select JavaScript API calls while the code inside the block executes.
        It does so by opening a CDP connection to the browser
        """
        pass

    @abstractmethod
    def get_calls(self) -> list:
        """Retrieve the list of intercepted API calls."""
        pass

    @abstractmethod
    def clear_calls(self):
        """Clear the list of intercepted API calls."""
        pass