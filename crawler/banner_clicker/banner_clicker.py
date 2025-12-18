from abc import ABC, abstractmethod
from lib.log import Logger

class BannerClicker(ABC):
    logger: Logger

    @abstractmethod
    def click_banner(self) -> dict:
        """Search and click on the banner, returning relevant data."""
        pass