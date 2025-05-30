from selenium.webdriver.common.bidi.cdp import CdpSession, BrowserError
from api_call_collector import ApiCallCollector
from types import ModuleType

class AttributionReportingApiCallCollector(ApiCallCollector):
    """
    Saves calls related to the Attribution Reporting API.

    Types of calls registered so far:
    - JavaScript calls to the `fetch` function with the `attributionReporting` option passed.
    - JavaScript calls to the `window.open()` function with the `attributionsrc[=...]` parameter passed.
    - CDP events:
        - `Storage.attributionReportingReportSent`
        - `Storage.attributionReportingSourceRegistered`
        - `Storage.attributionReportingTriggerRegistered`
    """
    
    def __init__(self):
        super().__init__()
        self.name = "attribution_reporting"
        self.js_calls_to_listen = [
            "fetch"
        ]

    def _set_devtools(self, devtools: ModuleType):
        self.cdp_events_to_listen = [
            devtools.storage.AttributionReportingReportSent,
            devtools.storage.AttributionReportingSourceRegistered,
            devtools.storage.AttributionReportingTriggerRegistered
        ]
        self._devtools = devtools

    async def init(self, session: CdpSession):
        assert self._devtools is not None
        try:
            await session.execute(self._devtools.storage.set_attribution_reporting_tracking(enable=True))
        except BrowserError as e:
            # In some contexts, Storage.setAttributionReportingTracking is not defined. Ignore in that case.
            if "wasn't found" not in e.message:
                raise e
    
    async def handle_js_call(self, payload: dict):
        if payload["description"] == "fetch":
            if payload["args"].get(1) and "attributionReporting" in payload["args"][1]:
                self.register_js_call(payload)
        elif payload["description"] == "open":
            if any(isinstance(arg, str) and "attributionsrc" in arg for arg in payload["args"]):
                self.register_js_call(payload)
        else:
            self.register_js_call(payload)

    async def handle_cdp_event(self, event):
        self.register_cdp_event(event)

    async def handle_db_connection(self, connection):
        # Do nothing
        return