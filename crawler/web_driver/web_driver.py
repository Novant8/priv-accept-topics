from abc import ABC, abstractmethod
from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver
from lib.log import Logger
from argparse import Namespace

class WebDriver(ABC, RemoteWebDriver):
    logger: Logger

    @abstractmethod
    def emulate_network_conditions(self, latency: int, download_throughput: int, upload_throughput: int):
        """Emulate network conditions for the WebDriver."""
        pass

    @abstractmethod
    def get_browsing_data(self) -> dict:
        """Retrieve browsing data collected during the session."""
        pass

    @abstractmethod
    def clear_status(self):
        """Clear the current status of the WebDriver."""
        pass

    @property
    @abstractmethod
    def user_data_dir(self) -> str:
        """Get the user data directory used by the WebDriver."""
        pass