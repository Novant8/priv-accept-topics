from selenium.webdriver.common.bidi.cdp import CdpSession, BrowserError
from api_call_collector import ApiCallCollector
from types import ModuleType
from typing import Union

class ProtectedAudienceApiCallCollector(ApiCallCollector):
    """
    Saves calls related to the Protected Audience API.

    Types of calls registered so far:
    - JavaScript calls to `navigator.join/leave/updateAdInterestGroup()`
    - JavaScript calls to `navigator.runAdAuction()`
    - CDP events:
        - `Storage.interestGroupAccessed`
        - `Storage.interestGroupAuctionEventOccurred`
        - `Storage.interestGroupAuctionNetworkRequestCreated`
    """

    def __init__(self):
        super().__init__()
        self.name = "protected_audience"
        self.js_calls_to_listen = [
            "Navigator.joinAdInterestGroup",
            "Navigator.leaveAdInterestGroup",
            "Navigator.updateAdInterestGroup",
            "Navigator.runAdAuction"
        ]

    def _set_devtools(self, devtools: ModuleType):
        self.cdp_events_to_listen = [
            devtools.storage.InterestGroupAccessed,
            devtools.storage.InterestGroupAuctionEventOccurred,
            devtools.storage.InterestGroupAuctionNetworkRequestCreated
        ]
        self._devtools = devtools

    async def init(self, session: CdpSession):
        assert self._devtools is not None
        try:
            await session.execute(self._devtools.storage.set_interest_group_tracking(enable=True))
            await session.execute(self._devtools.storage.set_interest_group_auction_tracking(enable=True))
        except BrowserError as e:
            # In some contexts, Storage.setInterestGroupTracking and ...AuctionTracking is not defined. Ignore in that case.
            if "wasn't found" not in e.message:
                raise e

    async def handle_js_call(self, payload: dict):
        self.register_js_call(payload)

    async def handle_cdp_event(self, event):
        self.register_cdp_event(event)