from selenium.webdriver.common.bidi.cdp import CdpSession
from types import ModuleType
from typing import Union, Optional
from abc import ABC, abstractmethod
from lib.db import DBConnection

class ApiCallCollector(ABC):
    """
    An API Collector saves the calls made to a specific Browser API.
    
    It reacts to the events intercepted by an API Interceptor, and saves (a subset of) the information passed by it.
    """

    name: str
    """
    The name of the API being collected.
    """

    _devtools: Optional[ModuleType]
    """
    The Devtools object with command and event definitions.
    Should be None at the beginning but should be set right after establishing a CDP connection to the browser.
    """

    js_calls: list[dict]
    """
    Collection of JavaScript call information saved so far.
    Contains the payloads passed by the interceptor.
    """

    cdp_events: list[any]
    """
    Collection of CDP events registered so far. Contains the event information as passed by the browser.
    """

    db_data: Optional[Union[list[dict], dict]]
    """
    Collection of data collected from a database.
    """

    js_calls_to_listen: list[str]
    """
    Collection of functions that this collector should listen to.
    
    The functions are specified as string literals in the format `elementType.functionName` (e.g. "Document.browsingTopics").
    Some functions (e.g., fetch) do not have an element type: in that case, only the function name is specified.
    """

    cdp_events_to_listen: list[type]
    """
    Collection of CDP events that this collector should listen to.

    The events are specified as their types, as defined in the automatically-generated DevTools library.
    """

    db_name: Optional[str]
    """
    Name of the database to connect to, if any, as saved in Chrome's configuration folder.
    """

    def __init__(self):
        self.name = "unknown"
        self._devtools = None
        self.js_calls = []
        self.cdp_events = []
        self.cdp_events_to_listen = []
        self.js_calls_to_listen = []
        self.db_name = None
        self.db_data = None

    @property
    def devtools(self):
        """
        Contains the DevTools object with command and event definitions.
        """
        return self._devtools

    @devtools.setter
    def devtools(self, devtools: ModuleType):
        """
        When the DevTools object is set, each collector should set the list of CDP events it should listen to.
        """
        self._set_devtools(devtools)

    @abstractmethod
    def _set_devtools(self, devtools):
        pass

    @abstractmethod
    async def init(session: CdpSession):
        """
        This function contains the initial steps to perform before the page/frame starts loading.
        E.g., if this collector needs to track Network events, it should fire the Network.enable command before the page/frame loads.
        """
        pass

    @abstractmethod
    async def handle_js_call(self, payload: dict):
        """
        Event listener for JavaScript calls.
        It is called everytime the interceptor detects a call to a tracked JavaScript function.

        The payload has the following structure:
        ```
        {
          "description": function_name,
          "accessType": "get",
          "args": [...],
          "source": script_url,
          "frameUrl": frame_url
        }
        ```
        """
        pass

    @abstractmethod
    async def handle_cdp_event(self, event: any):
        """
        Event listener for CDP events.
        It is called for every CDP event tracked by this collector.
        The event object can be of any type defined in the pre-generated devtools library.

        **Note**: This function is called only for events that are specified in the `self.cdp_events_to_listen` array.
        """
        pass

    @abstractmethod
    async def handle_db_connection(self, conn: DBConnection):
        """
        Event listener for when the interceptor connects to the database.
        The `conn` parameter can be used to execute SQL commands to retrieve data from the database.
        """
        pass

    def register_js_call(self, payload: dict):
        """
        Saves a JavaScript function's call data.
        """
        self.js_calls.append(payload)
    
    def register_cdp_event(self, event):
        """
        Saves a CDP event's data.
        """
        self.cdp_events.append(event)
    
    def clear_cdp_events(self):
        """
        Clears all CDP events registered so far.
        """
        self.cdp_events.clear()

    def clear_js_calls(self):
        """
        Clears all JavaScript function calls registered so far.
        """
        self.js_calls.clear()

    def clear_calls(self):
        """
        Clears all calls registered so far.
        """
        self.clear_cdp_events()
        self.clear_js_calls()