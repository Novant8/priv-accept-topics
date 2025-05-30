from selenium.webdriver.common.bidi.cdp import CdpSession
from api_call_collector import ApiCallCollector
from types import ModuleType

class TopicsApiCallCollector(ApiCallCollector):
    """
    Saves calls related to the Topics API.

    Types of calls registered so far:
    - JavaScript calls to the `fetch` function with the `browsingTopics` flag active.
    - JavaScript calls to `document.browsingTopics()`
    """
    
    def __init__(self):
        super().__init__()
        self.name = "topics"
        self.js_calls_to_listen = [
            "Document.browsingTopics",
            "fetch"
        ]

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

    async def handle_db_connection(self, connection):
        # Do nothing
        return