from argparse import Namespace
from web_crawler import WebCrawler
from web_driver import WebDriver
from lib.log import getLogger, getAllLoggerEntries
from api_interceptor import APICallInterceptor
from banner_clicker import BannerClicker
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By

import time
import trio
import os
import random

RUM_SPEED_INDEX_FILE="rum-speedindex.js"

class BannerCrawler(WebCrawler):
    stats: dict
    api_interceptor: APICallInterceptor
    banner_clicker: BannerClicker

    def __init__(self, args: Namespace, driver: WebDriver, api_interceptor: APICallInterceptor, banner_clicker: BannerClicker):
        super().__init__()
        self.args = args
        self.driver = driver
        self.logger = getLogger(__name__)
        self.stats = {}
        self.api_interceptor = api_interceptor
        self.banner_clicker = banner_clicker

        # Init basic stats
        self.stats["lang"] = args.lang if args.lang is not None else "default"
        self.stats["headless"] = args.headless
    
    async def crawl_website(self, url: str) -> dict:
        """
        Crawl the given URL and return the banner information.

        Args:
            url (str): The URL to crawl.

        Returns:
            data (dict): A dictionary containing the banner information and other collected data.
        """

        url = self._normalize_url(url)
        
        # Emulate network conditions if specified
        if self.args.network_conditions:
            latency, download, upload = [int(e) for e in self.args.network_conditions.split(":")]
            self.driver.emulate_network_conditions(latency, download, upload)

        # Perform pre-visit if specified
        self.stats["pre-visit"] = self.args.pre_visit
        pre_visit_data = None
        if self.args.pre_visit:
            self.logger.info("Making Pre-First Visit")
            async with self.api_interceptor.intercept():
                await trio.to_thread.run_sync(self._perform_visit, url, "pre")
            self.logger.info("Getting data of pre-visit")
            pre_visit_data = self._get_data()

        # Perform first visit
        self.logger.info(f"Making First Visit to {url}")
        async with self.api_interceptor.intercept():
            await trio.to_thread.run_sync(self._perform_visit, url, "first")
        self.logger.info("Getting data of first visit")
        before_data = self._get_data()

        # Search for banner (try to scroll if specified)
        self.logger.info("Searching banner")
        self.stats["has-scrolled"] = self.args.try_scroll
        if self.args.try_scroll:
            self._try_scroll()
        banner_data = self.banner_clicker.click_banner()
        banner_found = "clicked_element" in banner_data or (banner_data.get("double_click") and banner_data.get("button_data") and banner_data["button_data"].get("clicked_element"))
        self.stats["has-found-banner"] = banner_found

        # If banner was found, collect post-click data
        click_data = None
        if banner_found or self.args.force_click_data:
            async with self.api_interceptor.intercept():
                await trio.sleep(self.args.timeout)
            
            self.logger.info("Getting data of post-click")
            click_data = self._get_data()
            self._take_screenshot("{}/all-click.png".format(self.args.screenshot_dir))
            self.logger.info("URL after click: {}".format(self.driver.current_url))
            self.stats["after-click-landing-page"] = self.driver.current_url

        # If banner was found, proceed with second visit
        after_data = None
        if banner_found or self.args.force_second_visit:
            #  Go to the page, second visit
            self.logger.info("Making the Second Visit")
            self.stats["has-cleared-cache"] = False
            if self.args.clear_cache:
                self.driver.clear_status()
                self.stats["has-cleared-cache"] = True
            # Clean last page
            self.driver.get("about:blank")
            self._get_data()  # Clean data
            time.sleep(self.args.timeout)
            
            async with self.api_interceptor.intercept():
                await trio.to_thread.run_sync(self._perform_visit, url, "second")
            
            self.logger.info("Getting data of second visit")
            after_data = self._get_data()
            self._take_screenshot("{}/all-second.png".format(self.args.screenshot_dir))
        else:
            self.logger.info("Banner not found, skipping second visit")

        # Visit internal pages if specified
        internal_data = None
        if self.args.visit_internals:
            internal_urls_to_visit = self._get_internal_urls(self.args.num_internal)

            async with self.api_interceptor.intercept():
                for i,internal_url in enumerate(internal_urls_to_visit):
                    self.logger.info("Visiting internal URL: {}".format(internal_url ))
                    try:
                        await trio.to_thread.run_sync(self._perform_visit, internal_url, f"internal-{i}")
                        self._take_screenshot("{}/all-internal-{}.png".format(self.args.screenshot_dir, i))
                    except TimeoutException:
                        self.logger.warning("Could not load URL {} before timeout.".format(internal_url))
            self.logger.info("Getting data of internal page visits")
            internal_data = self._get_data()
        
        # Return data
        data = {
            "pre_visit": pre_visit_data,
            "first": before_data, "click": click_data, "second": after_data, "banner_data": banner_data,
            "log": getAllLoggerEntries(), "stats": self.stats, "internal":internal_data
        }
        return data

    def _get_data(self) -> dict:
        """
        Retrieve browsing data collected during the session.
        """
        data = self.driver.get_browsing_data(self.args.full_net_log)
        data["api_calls"] = self.api_interceptor.get_calls()
        return data
    
    def _perform_visit(self, url: str, name: str):
        """
        Perform a single visit to the given URL and collect performance metrics.

        Args:
            url (str): The URL to visit.
            name (str): The name identifier for this visit (e.g., "first", "second").
        """

        self.stats["target"] = url
        self.stats["start-time"] = time.time()

        start_time=time.time()
        self.driver.get(url)
        end_time=time.time()
        
        # Calculate RUM Speed Index if specified
        if self.args.rum_speed_index:
            self.stats["collect-rum-speed-index"] = True
            rsi = self.driver.execute_script(open(RUM_SPEED_INDEX_FILE, "r").read() + "; return RUMSpeedIndex(); " )
            self.stats[f"{name}-visit-rum-speed-index"] = rsi
        
        self.logger.info("{} Visit Selenium time [s]: {}".format(name.capitalize(), end_time-start_time))
        self.stats[f"{name}-visit-selenium-time"] = end_time-start_time
        self.logger.info("Landed to: {}".format(self.driver.current_url))
        self.stats[f"{name}-visit-landing-page"] = self.driver.current_url
        time.sleep(self.args.timeout)
        self.stats[f"{name}-visit-timings"] = self.driver.execute_script("var performance = window.performance || {}; var timings = performance.timing || {}; return timings;")

    def _try_scroll(self):
        self.logger.info("Scrolling to the bottom")
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(self.args.timeout)
        self.logger.info("Scrolling to the top")
        self.driver.execute_script("window.scrollTo(0, 0)")
        self.stats["has-scrolled"] = True

    def _take_screenshot(self, file_path: str):
        if self.args.screenshot_dir is not None:
            if not os.path.exists(self.args.screenshot_dir):
                os.makedirs(self.args.screenshot_dir)
            try:
                self.driver.save_screenshot(file_path)
            except Exception as e:
                self.logger.info("Exception in making screenshot: {}".format(e))

    def _get_internal_urls(self, max_urls: int) -> list[str]:
        internal_urls = set()
        eles = self.driver.find_elements(By.XPATH, "//*[@href]")
        for elem in eles:
            url = elem.get_attribute('href').split("#")[0]
            #if url.startswith(driver.current_url) and url!=driver.current_url:
            domain_url = url.split("/")[2] if len (url.split("/")) >=3 else None
            landing_domain = self.driver.current_url.split("/")[2] if len (self.driver.current_url.split("/")) >=3 else None
            if domain_url == landing_domain and url != self.driver.current_url:
                internal_urls.add(url)
        if len(internal_urls) >= max_urls:
            internal_urls_to_visit = random.sample(sorted(internal_urls), max_urls)
        else:
            self.logger.warning("Only {} internal URLs to visit".format(len(internal_urls)) )
            internal_urls_to_visit = list(internal_urls)
        return internal_urls_to_visit

    def _normalize_url(self, url: str) -> str:
        """Normalize the given URL, adding https:// if missing."""

        url = (url or "").strip()
        # Keep about: URLs as-is
        if url.startswith("about:"):
            return url
        if not (url.startswith("http://") or url.startswith("https://")):
            return "https://" + url
        return url