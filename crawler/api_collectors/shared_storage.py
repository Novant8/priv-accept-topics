from selenium.webdriver.common.bidi.cdp import CdpSession, BrowserError
from api_call_collector import ApiCallCollector
from types import ModuleType

class SharedStorageApiCallCollector(ApiCallCollector):
    """
    Saves calls related to the Shared Storage API.

    Types of calls registered so far:
    - JavaScript calls:
        - `sharedStorage.get`/`set`/`append`/`delete`/`batchUpdate`/`clear`
        - `sharedStorage.createWorklet`
        -`fetch` with the `sharedStorageWritable` flag active.
    - CDP events:
        - Storage.sharedStorageAccessed
        - Storage.sharedStorageWorkletOperationExecutionFinished
    """
    
    def __init__(self):
        super().__init__()
        self.name = "shared_storage"
        self.js_calls_to_listen = [
            "SharedStorage.get",
            "SharedStorage.set",
            "SharedStorage.append",
            "SharedStorage.delete",
            "SharedStorage.batchUpdate",
            "SharedStorage.clear",
            "SharedStorage.createWorklet",
            "SharedStorageWorklet.addModule",
            "fetch"
        ]

    def _set_devtools(self, devtools: ModuleType):
        self.cdp_events_to_listen = [
            devtools.storage.SharedStorageAccessed,
            devtools.storage.SharedStorageWorkletOperationExecutionFinished
        ]
        self._devtools = devtools

    async def init(self, session: CdpSession):
        assert self._devtools is not None
        try:
            await session.execute(self._devtools.storage.set_shared_storage_tracking(enable=True))
        except BrowserError as e:
            # In some contexts, Storage.setInterestGroupTracking and ...AuctionTracking is not defined. Ignore in that case.
            if "wasn't found" not in e.message:
                raise e
    
    async def handle_js_call(self, payload: dict):
        if payload["description"] == "fetch":
            if payload["args"].get(1) and "sharedStorageWritable" in payload["args"][1]:
                self.register_js_call(payload)
        else:
            self.register_js_call(payload)

    async def handle_cdp_event(self, event):
        self.register_cdp_event(event)

    async def handle_db_connection(self, connection):
        # Do nothing
        return