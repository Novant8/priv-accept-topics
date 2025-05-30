from selenium.webdriver.common.bidi.cdp import CdpSession, BrowserError
from api_call_collector import ApiCallCollector
from types import ModuleType

class RelatedWebsiteSetsApiCallCollector(ApiCallCollector):
    """
    Saves calls related to the Related Website Sets API.

    Types of calls registered so far:
    - JavaScript calls to `requestStorageAccess` and `requestStorageAccessFor`
    """
    
    def __init__(self):
        super().__init__()
        self.name = "related_website_sets"
        self.js_calls_to_listen = [
            "Document.requestStorageAccess",
            "Document.requestStorageAccessFor"
        ]

    def _set_devtools(self, devtools: ModuleType):
        self.cdp_events_to_listen = [
            # No CDP events
        ]
        self._devtools = devtools

    async def init(self, session: CdpSession):
        # Do nothing
        return
    
    async def handle_js_call(self, payload: dict):
        self.register_js_call(payload)

    async def handle_cdp_event(self, event):
        self.register_cdp_event(event)

    async def handle_db_connection(self, connection):
        # Do nothing
        return