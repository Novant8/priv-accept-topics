from argparse import Namespace
from .web_driver import WebDriver
import json
from lib.log import getLogger

from selenium.webdriver import Chrome as SeleniumChromeDriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

class ChromeWebDriver(SeleniumChromeDriver, WebDriver):
    headless: bool
    
    def __init__(
            self,
            args: Namespace,
            desired_capabilities: dict = DesiredCapabilities.CHROME,
            options: Options = Options(),
            **kwargs
        ):
        """Initialize the Chrome WebDriver with given arguments."""
        self.logger = getLogger(__name__)
        self.headless = args.headless

        self.logger.info("Starting Driver")
        # d['loggingPrefs'] = { 'performance':'ALL' }
        desired_capabilities['goog:loggingPrefs'] = {'performance': 'ALL'}

        options.capabilities.update(desired_capabilities)

        if args.chrome_binary:
            options.binary_location = args.chrome_binary

        #if args.user_agent is not None:
        #    USER_AGENT_DEFAULT = args.user_agent

        # Enable Privacy Sandbox APIs
        if not args.disable_privacy_sandbox:
            options.add_argument("enable-privacy-sandbox-ads-apis")
            
        if args.lang is not None:
            options.add_experimental_option('prefs', {'intl.accept_languages': args.lang})
            
        if args.headless:
            options.headless = True
            options.add_argument("window-size=1920,1080")
            #options.add_argument("user-agent={}".format(USER_AGENT_DEFAULT))
            
        if args.user_agent is not None:
            options.add_argument("user-agent={}".format(args.user_agent))
            
        if args.docker:
            options.add_argument("no-sandbox")
            options.add_argument("disable-dev-shm-usage")

        for option in args.chrome_extra_option:
            options.add_argument(option)

        service = Service(executable_path=args.chrome_driver)
        
        super().__init__(service=service, options=options, **kwargs)

    def emulate_network_conditions(self, latency: int, download: int, upload: int):
        """ Emulate network conditions for the WebDriver. """
        self.execute_cdp_cmd('Network.emulateNetworkConditions', {"latency": latency,
                                                                    "downloadThroughput": download,
                                                                    "uploadThroughput": upload,
                                                                    "offline": False})
    
    def get_browsing_data(self, full_net_log: int) -> dict:
        """Retrieve browsing data collected during the session."""
        if full_net_log:
            data = { "requests": [], "responses": [], "responses-extra": [],
                    "cookies": self.driver.execute_cdp_cmd('Network.getAllCookies', {})}
        else:
            data = { "urls": [],
                    "cookies": self.execute_cdp_cmd('Network.getAllCookies', {})}

        log = self.get_log('performance')

        for entry in log:
            message = json.loads(entry["message"])
            if full_net_log:
                if message["message"]["method"] == "Network.responseReceived":
                    data["responses"].append(message["message"]["params"])
                elif message["message"]["method"] == "Network.responseReceivedExtraInfo":
                    data["responses-extra"].append(message["message"]["params"])
                elif message["message"]["method"] == "Network.requestWillBeSent":
                    data["requests"].append(message["message"]["params"])
            else:
                if message["message"]["method"] == "Network.responseReceived":
                    url = message["message"]["params"]["response"]["url"]
                    data["urls"].append(url)

        return data

    def clear_status(self):
        """Clear the current status of the WebDriver."""
        self.execute_cdp_cmd('Network.clearBrowserCache', {})
        if not self.headless:
            self.get("chrome://net-internals/#sockets")
            self.find_element(By.ID, "sockets-view-flush-button").click()
            self.get("chrome://net-internals/#dns")
            self.find_element(By.ID, "dns-view-clear-cache").click()
        else:
            self.logger.info("Warning: cannot clean DNS and socket cache in headless mode.")# 

    @property
    def user_data_dir(self) -> str:
        """Get the user data directory used by the WebDriver."""
        return self.capabilities.get("chrome", {}).get("userDataDir", "")