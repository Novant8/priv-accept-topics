from argparse import Namespace
from .web_driver import WebDriver
from lib.log import getLogger

import os
import shutil
import sqlite3

from selenium.webdriver import Firefox as SeleniumFirefoxDriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile

class FirefoxWebDriver(SeleniumFirefoxDriver, WebDriver):
    headless: bool
    profile: FirefoxProfile
    
    def __init__(
            self,
            args: Namespace,
            desired_capabilities: dict = DesiredCapabilities.FIREFOX,
            options: Options = Options(),
            **kwargs
        ):
        """Initialize the Firefox WebDriver with given arguments."""
        self.logger = getLogger(__name__)
        self.headless = args.headless

        self.logger.info("Starting Driver")
        # Enable logging for network activity
        #desired_capabilities['loggingPrefs'] = {'performance': 'ALL'}

        options.capabilities.update(desired_capabilities)

        if args.firefox_binary is not None:
            options.binary_location = args.firefox_binary

        # Privacy Sandbox APIs are Chrome-specific
        if not args.disable_privacy_sandbox:
            self.logger.warning("Privacy Sandbox APIs are Chrome-specific and not available in Firefox")
            
        if args.lang is not None:
            options.set_preference('intl.accept_languages', args.lang)
            
        if args.headless:
            options.headless = True
            options.add_argument("--width=1920")
            options.add_argument("--height=1080")
            
        if args.user_agent is not None:
            options.set_preference("general.useragent.override", args.user_agent)
            
        if args.docker:
            options.add_argument("--no-sandbox")
            # disable-dev-shm-usage is Chrome-specific
            self.logger.warning("Some Docker options are Chrome-specific and may not apply to Firefox")

        for option in args.extra_option:
            options.add_argument(option)

        # Disable cache if specified
        if args.clear_cache:
            options.set_preference("browser.cache.disk.enable", False)
            options.set_preference("browser.cache.memory.enable", False)
            options.set_preference("browser.cache.offline.enable", False)
            options.set_preference("network.http.use-cache", False)

        service = Service(executable_path=args.firefox_driver)
        
        super().__init__(service=service, options=options, **kwargs)

    def emulate_network_conditions(self, latency: int, download: int, upload: int):
        """ Emulate network conditions for the WebDriver. """
        self.logger.warning("Network conditions emulation is not directly supported in Firefox WebDriver")
    
    def get_browsing_data(self, full_net_log: int) -> dict:
        """Retrieve browsing data collected during the session."""
        self.logger.warning("Performance log collection in Firefox is limited compared to Chrome")
        
        # Firefox doesn't support CDP commands like Chrome
        data = {"urls": [], "cookies": []}
        
        try:
            # Get cookies using standard WebDriver API
            cookies = self._get_cookies_via_db()
            data["cookies"] = cookies
        except Exception as e:
            self.logger.warning(f"Could not retrieve cookies: {e}")
            
        if full_net_log:
            self.logger.warning("Full network logging is not available in Firefox WebDriver")
            data["requests"] = []
            data["responses"] = []
            data["responses-extra"] = []

        return data

    def clear_status(self):
        """Clear the current status of the WebDriver."""
        # Clear cookies and local storage
        try:
            self.delete_all_cookies()
            self.execute_script("localStorage.clear();")
            self.execute_script("sessionStorage.clear();")
        except Exception as e:
            self.logger.warning(f"Could not clear browser data: {e}")

    def _get_cookies_via_db(self):
        """Retrieve cookies directly from Firefox's SQLite database."""

        try:
            profile_path = self.user_data_dir
            cookies_db_path = os.path.join(profile_path, "cookies.sqlite")
            if not os.path.exists(cookies_db_path):
                self.logger.error("Cookies database not found at {}".format(cookies_db_path))
                return []

            # Copy the database to avoid locking issues
            temp_db_path = os.path.join(profile_path, "cookies_temp.sqlite")
            shutil.copy2(cookies_db_path, temp_db_path)

            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()
            
            # Get column names from the database schema
            cursor.execute("PRAGMA table_info(moz_cookies)")
            columns = [column[1] for column in cursor.fetchall()]
            
            cursor.execute("SELECT * FROM moz_cookies")
            rows = cursor.fetchall()
            cookies = [ dict(zip(columns, row)) for row in rows ]
            conn.close()
            os.remove(temp_db_path)
        except Exception as e:
            self.logger.error("Error retrieving cookies from database: {}".format(e))
        return cookies

    @property
    def user_data_dir(self) -> str:
        """Get the user data directory used by the WebDriver."""
        return self.capabilities.get('moz:profile', '')