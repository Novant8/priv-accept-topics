from argparse import Namespace
from .banner_clicker import BannerClicker

from lib.log import getLogger
from web_driver import WebDriver
from selenium.webdriver.common.by import By

import time
import os

GLOBAL_SELECTOR = "a, button, div, span, form, p"
    
class KeywordBannerClicker(BannerClicker):
    name: str
    driver: WebDriver
    keywords: set[str]
    option_keywords: set[str]
    timeout: int
    screenshot_dir: str | None

    def __init__(self, name: str, driver: WebDriver, keyword_file: str, option_keyword_file: str, args: Namespace):
        super().__init__()
        self.name = name
        self.driver = driver
        self.logger = getLogger(__name__)
        self.timeout = args.timeout
        self.screenshot_dir = args.screenshot_dir

        # Read keywords from file
        with open(keyword_file, "r", encoding="utf-8") as f:
            self.keywords = set(line.strip().lower() for line in f if line.strip())

        # Read option keywords from file
        with open(option_keyword_file, "r", encoding="utf-8") as f:
            self.option_keywords = set(line.strip().lower() for line in f if line.strip())

    def click_banner(self) -> dict:
        banner_data = self._search_iframe_banner(self.keywords)
        if banner_data is None:
            self.logger.info("Searching and Performing Two-Step Click (Option → Deny)")
            first_result, second_result = self._double_click_banner()
            banner_data = {
                "double_click": True,
                "option_data": first_result,
                "button_data": second_result
            }
        else:
            banner_data["double_click"] = False
        return banner_data
    
    def _search_iframe_banner(self, keywords: list[str], screenshot_name="clicked_element"):
        banner_data = self._click_banner(keywords, screenshot_name=screenshot_name)
        if banner_data.get("clicked_element"):
            self.driver.switch_to.default_content()
            return banner_data
        iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            try:
                self.logger.info(f"Searching for banner in iframe: {iframe.id}")
                self.driver.switch_to.frame(iframe)
                internal_banner_data = self._search_iframe_banner(keywords, screenshot_name=screenshot_name)
                if internal_banner_data:
                    return internal_banner_data
            except:
                self.logger.info("Exception while searching banner in iframe: {}".format(iframe.id))
            finally: 
                self.driver.switch_to.default_content()
        return None
    
    def _click_banner(self, keyword_list: set[str], screenshot_name="clicked_element") -> dict:

        banner_data = {"matched_containers": [], "candidate_elements": []}
        contents = self.driver.find_elements(By.CSS_SELECTOR, GLOBAL_SELECTOR)

        candidates = []

        for c in contents:
            try:
                if c.text.lower().strip(" ✓›!→x>\n").replace('\n', ' ') in keyword_list:
                    candidates.append(c)
                    banner_data["candidate_elements"].append({"id": c.id,
                                                            "tag_name": c.tag_name,
                                                            "text": c.text,
                                                            "size": c.size,
                                                            "signature": self._get_signature(c),
                                                            })
            except:
                self.logger.info("Exception in processing element: {}".format (c.id) )
        
        # Click the candidate    
        if len(candidates) > 0:
            self.logger.info("Found {} maching candidate(s)".format(len(candidates)))
            for candidate in candidates:
                try: # in some pages element is not clickable
                    if self.screenshot_dir is not None:
                        if not os.path.exists(self.screenshot_dir):
                            os.makedirs(self.screenshot_dir)
                        try:
                            candidate.screenshot("{}/{}.png".format(self.screenshot_dir, screenshot_name))
                        except Exception as e:
                            self.logger.info("Exception in making screenshot: {}".format(e))
                    self.logger.info("Clicking text: {}".format (candidate.text.lower().strip(" ✓›!\n")) )
                    candidate.click()
                    banner_data["clicked_element"] = candidate.id
                    self.logger.info("Clicked: {}".format (candidate.id) )
                    break
                except:
                    self.logger.info("Exception in candidate click: {}".format(candidate.id) )
        else:
            self.logger.info("Warning, no matching candidate")
        return banner_data
    
    def _double_click_banner(self) -> tuple[dict, dict]:
        # First click: option_words
        self.logger.info("Searching for Options button")
        first_result = self._search_iframe_banner(self.option_keywords, screenshot_name="option_button")
        if first_result is None or not first_result.get("clicked_element"):
            return first_result, None
        time.sleep(self.timeout)
        self.logger.info("Searching for {} button".format(self.name))
        second_result = self._search_iframe_banner(self.keywords, screenshot_name=f"{self.name}_button")
        return first_result, second_result

    def _get_signature(element):

        def props_to_dict(e):
            props = {"tag": e.tag_name }
            for attr in e.get_property('attributes'):
                props[attr['name']] = attr['value']
            return props
            
        signature = []
        current = element
        while True:
            signature.insert(0, props_to_dict(current))
            
            if current.tag_name == "html":
                break
            current = current.find_element(By.XPATH, '..')
            if current == None:
                break
            
        return signature