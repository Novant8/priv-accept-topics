from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.bidi.cdp import connect_cdp, connection_context, import_devtools, CdpConnection, CdpSession
from contextlib import asynccontextmanager
import json
import trio
from types import ModuleType

with open("intercept-api-calls.js") as file:
    INTERCEPT_CALLS_SCRIPT = file.read()

class APICallInterceptor:
    driver: WebDriver
    calls: list
    script_loaded: bool

    def __init__(self, driver: WebDriver):
        self.calls = list()
        self.driver = driver
        self.script_loaded = False

    @asynccontextmanager
    async def _open_cdp_session(self, nursery: trio.Nursery):
        """
        Opens a CDP connection and attaches to the main page's session.
        The CDP connection exits when the block exits.
        """
        version,ws_url = self.driver._get_cdp_details()
        devtools = import_devtools(version)
        
        conn = await connect_cdp(nursery, ws_url)
        try:
            with connection_context(conn):
                targets = await conn.execute(devtools.target.get_targets())
                page_target = next((target for target in targets if target.type_ == "page"), None)
                if page_target is None:
                    raise RuntimeError("No page target found.")
                target_id = page_target.target_id
                async with conn.open_session(target_id) as session:
                    yield conn, session, devtools
        finally:
            await conn.aclose()

    async def _handle_target_created(self, session: CdpSession, conn: CdpConnection, devtools: ModuleType, nursery: trio.Nursery):
        """
        Event handler for the Target.targetCreated and Target.attachedToTarget events.
        Creates new sessions for each target discovered and initializes them.
        """
        async for event in session.listen(devtools.target.TargetCreated, devtools.target.AttachedToTarget):
            target_id = event.target_info.target_id

            # Create only one session per target
            found_session = next((session for session in conn.sessions.values() if session.target_id == target_id), None)
            if found_session is None:
                if isinstance(event, devtools.target.TargetCreated):
                    # Target created but not attached: attach and create new session
                    new_session = await conn.connect_session(target_id)
                else:
                    # Target attached: create new session only
                    new_session = CdpSession(conn.ws, event.session_id, target_id)
                    conn.sessions[event.session_id] = new_session
                await self._init_session(conn, new_session, devtools, nursery, target_type=event.target_info.type_)

    async def _handle_binding_called(self, session: CdpSession, devtools: ModuleType):
        """
        Event handler for the Runtime.bindingCalled event.
        Saves all payloads in `self.calls`.
        """
        async for event in session.listen(devtools.runtime.BindingCalled):
            if event.name == "calledAPIEvent":
                payload = json.loads(event.payload)
                self.calls.append(payload)

    async def _init_session(self, conn: CdpConnection, session: CdpSession, devtools: ModuleType, nursery: trio.Nursery, target_type = "unknown"):
        """
        Performs the preliminary steps to track function calls within the given session
        """
        # Auto-attach to new targets and wait for debugger on start: this is to allow captuing all information
        await session.execute(devtools.target.set_auto_attach(auto_attach=True, wait_for_debugger_on_start=True, flatten=True))

        # Start event listener tasks
        nursery.start_soon(self._handle_target_created, session, conn, devtools, nursery)
        nursery.start_soon(self._handle_binding_called, session, devtools)

        # Add binding for recording API calls
        await session.execute(devtools.runtime.add_binding(name="calledAPIEvent"))
        
        if target_type in ["page", "iframe"]:
            # Enable page commands and event logging
            await session.execute(devtools.page.enable())

            # Inject 'intercept-functions.js' script on all new documents (pages and iframes)
            await session.execute(devtools.page.add_script_to_evaluate_on_new_document(source=INTERCEPT_CALLS_SCRIPT))

        # Enable runtime event logging (needed for Runtime.bindingCalled event)
        await session.execute(devtools.runtime.enable())

        # Resume only after having initialized everything
        await session.execute(devtools.runtime.run_if_waiting_for_debugger())

    @asynccontextmanager
    async def intercept(self):
        """
        This async context manager intercepts select JavaScript API calls while the code inside the block executes.
        It does so by opening a CDP connection to the browser
        """
        async with trio.open_nursery() as nursery:
            async with self._open_cdp_session(nursery) as (conn, session, devtools):
                await self._init_session(conn, session, devtools, nursery, target_type="page")

                try:
                    yield conn, session, devtools
                finally:
                    nursery.cancel_scope.cancel()

    def get_calls(self):
        return self.calls.copy()
    
    def clear_calls(self):
        self.calls.clear()