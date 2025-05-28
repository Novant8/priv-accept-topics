from selenium.webdriver.common.bidi.cdp import CdpSession, BrowserError
from api_call_collector import ApiCallCollector
from types import ModuleType

class FedCMApiCallCollector(ApiCallCollector):
    """
    Saves calls related to the Federated Credential Management API.

    Types of calls registered so far:
    - JavaScript calls to `navigator.credentials.get()` (recorded as `CredentialsContainer.get()`).
    - FedCm.dialogShown CDP event.
    """
    
    def __init__(self):
        super().__init__()
        self.name = "fedcm"
        self.js_calls_to_listen = [
            "CredentialsContainer.get"
        ]

    def _set_devtools(self, devtools: ModuleType):
        self.cdp_events_to_listen = [
            devtools.fed_cm.DialogShown
        ]
        self._devtools = devtools

    async def init(self, session: CdpSession):
        try:
            await session.execute(self._devtools.fed_cm.enable())
        except BrowserError as e:
            # In some contexts, FedCm.enable is not defined. Ignore in that case.
            if "wasn't found" not in e.message:
                raise e
        return
    
    async def handle_js_call(self, payload: dict):
        self.register_js_call(payload)

    async def handle_cdp_event(self, event):
        self.register_cdp_event(event)