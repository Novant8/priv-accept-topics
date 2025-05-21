from selenium.webdriver.common.bidi.cdp import CdpSession
from api_call_collector import ApiCallCollector
from types import ModuleType

class PrivateStateTokensApiCallCollector(ApiCallCollector):
    """
    Saves calls related to the Private State Tokens API.

    Types of calls registered so far:
    - JavaScript calls to the `fetch` function with the `privateToken` option passed.
    - JavaScript calls to `document.hasPrivateToken()` and `document.hasRedemptionRecord`.
    - `Network.trustTokenOperationDone` CDP event **(WIP)**
    """

    def __init__(self):
        super().__init__()
        self.name = "private_state_tokens"
        self.js_calls_to_listen = [
            "Document.hasPrivateToken",
            "Document.hasRedemptionRecord",
            "fetch"
        ]

    def _set_devtools(self, devtools: ModuleType):
        self.cdp_events_to_listen = [
            devtools.network.TrustTokenOperationDone
        ]
        self._devtools = devtools

    async def init(self, session: CdpSession):
        assert self._devtools is not None
        # await session.execute(self._devtools.network.enable()) # FIXME: json['expires'] is None instead of a number??
        return
    
    async def handle_js_call(self, payload: dict):
        if payload["description"] == "fetch":
            if payload["args"].get(1) and "privateToken" in payload["args"][1]:
                self.register_js_call(payload)
        else:
            self.register_js_call(payload)

    async def handle_cdp_event(self, event):
        self.register_cdp_event(event)