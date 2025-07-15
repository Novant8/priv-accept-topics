from selenium.webdriver.common.bidi.cdp import CdpSession
from api_call_collector import ApiCallCollector
from types import ModuleType
from lib.db import DBConnection

class TopicsApiCallCollector(ApiCallCollector):
    """
    Saves calls related to the Topics API.

    Types of calls registered so far:
    - JavaScript calls to the `fetch` function with the `browsingTopics` flag active.
    - JavaScript calls to `document.browsingTopics()`
    """

    custom_chromium: bool
    last_usage_time: int
    
    def __init__(self, custom_chromium = False):
        super().__init__()
        self.name = "topics"
        self.js_calls_to_listen = [
            "Document.browsingTopics",
            "fetch"
        ]
        self.db_name = "BrowsingTopicsSiteData"
        self.custom_chromium = custom_chromium
        self.last_usage_time = 0

    def _set_devtools(self, devtools: ModuleType):
        self.cdp_events_to_listen = [
            # No CDP Events
        ]
        self._devtools = devtools

    async def init(self, session: CdpSession):
        # Do nothing
        return
    
    async def handle_js_call(self, payload: dict):
        if payload["description"] == "fetch":
            if payload["args"].get(1) and "browsingTopics" in payload["args"][1]:
                self.register_js_call(payload)
        else:
            self.register_js_call(payload)

    async def handle_cdp_event(self, event):
        self.register_cdp_event(event)

    async def handle_db_connection(self, conn: DBConnection):
        if self.custom_chromium:
            # Custom Chromium allows to retrieve the caller source (i.e., javascript, fetch or iframe)
            sql = f"""
                SELECT context_origin_url, caller_source, hashed_main_frame_host, usage_time
                FROM browsing_topics_api_usages_complete, browsing_topics_api_hashed_to_unhashed_domain
                WHERE browsing_topics_api_usages_complete.hashed_context_domain = browsing_topics_api_hashed_to_unhashed_domain.hashed_context_domain
                AND usage_time > ?
            """
        else:
            sql = """
                SELECT context_domain, hashed_main_frame_host, last_usage_time
                FROM browsing_topics_api_usages, browsing_topics_api_hashed_to_unhashed_domain
                WHERE browsing_topics_api_usages.hashed_context_domain = browsing_topics_api_hashed_to_unhashed_domain.hashed_context_domain
                AND last_usage_time > ?
            """
        
        self.logger.debug(f"Attempting connection to database '{self.db_name}'")
        cur = conn.cursor()
        self.logger.debug(f"Connection to '{self.db_name}' successful")
        res = cur.execute(sql, [self.last_usage_time])
        self.logger.debug(f"Executing query:\n{sql}")
        self.db_data = []
        for row in res.fetchall():            
            if self.custom_chromium:
                row_dict = {
                    "context_origin_url": row[0],
                    "caller_source": row[1],
                    "hashed_main_frame_host": row[2],
                    "usage_time": row[3]
                }
            else:
                row_dict = {
                    "context_domain": row[0],
                    "hashed_main_frame_host": row[1],
                    "last_usage_time": row[2]
                }
            self.db_data.append(row_dict)

            usage_time = row[3] if self.custom_chromium else row[2]
            if usage_time > self.last_usage_time:
                self.last_usage_time = usage_time
        self.logger.debug(f"Current DB data for '{self.name}': {self.db_data}")