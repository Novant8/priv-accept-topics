from selenium.webdriver.common.bidi.cdp import CdpSession
from api_call_collector import ApiCallCollector
from types import ModuleType

class FencedFramesApiCallCollector(ApiCallCollector):
    """
    Saves calls related to the Fenced Frames API.

    Types of calls registered so far:
    - Target.Created, Target.AttachedToTarget, Target.TargetInfoChanged CDP events for fenced frames.
    """
    
    def __init__(self):
        super().__init__()
        self.name = "fenced_frames"
        self.js_calls_to_listen = [
            # No JS calls
        ]

    def _set_devtools(self, devtools: ModuleType):
        self.cdp_events_to_listen = [
            devtools.target.TargetCreated,
            devtools.target.AttachedToTarget,
            devtools.target.TargetInfoChanged
        ]
        self._devtools = devtools

    async def init(self, session: CdpSession):
        # Do nothing
        return
    
    async def handle_js_call(self, payload: dict):
        self.register_js_call(payload)

    async def handle_cdp_event(self, event):
        if isinstance(event, (self._devtools.target.TargetCreated, self._devtools.target.AttachedToTarget)):
            # Save newly created fenced frames
            if (event.target_info.type_ == "iframe" and event.target_info.subtype == "fenced"):
                self.register_cdp_event(event)
        else:
            # Keep track of TargetInfoChanged events of fenced frames already found, as they may contain a URL for the frame
            fenced_frame_created = next((e for e in self.cdp_events if e.target_info.target_id == event.target_info.target_id), None)
            if fenced_frame_created is not None:
                self.register_cdp_event(event)

    async def handle_db_connection(self, connection):
        # Do nothing
        return