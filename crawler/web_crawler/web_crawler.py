from abc import ABC, abstractmethod
from argparse import Namespace
from web_driver import WebDriver
from logging import Logger

class WebCrawler(ABC):
    args: Namespace
    driver: WebDriver
    logger: Logger

    @abstractmethod
    async def crawl_website(self, url: str) -> dict:
        """Perform crawling and data collection from the given URL."""
        pass