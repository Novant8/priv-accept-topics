from contextlib import asynccontextmanager
import os
from api_call_collector import ApiCallCollector
from api_interceptor import APICallInterceptor
from lib.log import getLogger

with open(os.path.dirname(os.path.realpath(__file__)) + "/assets/intercept-api-calls.js") as file:
    INTERCEPT_CALLS_SCRIPT = file.read()

class EmptyCallInterceptor(APICallInterceptor):
    """An API interceptor that does nothing. Used when no interception is desired."""

    def __init__(self, collectors: list[ApiCallCollector] = []):
        self.logger = getLogger(__name__)
        self.collectors = collectors

    @asynccontextmanager
    async def intercept(self):
        yield None, None, None

    def get_calls(self) -> dict:
        self.logger.debug("EmptyInterceptor.get_calls() called, returning empty data.")
        return {collector.name: [] for collector in self.collectors}
    
    def clear_calls(self):
        self.logger.debug("EmptyInterceptor.clear_calls() called, but nothing to clear.")