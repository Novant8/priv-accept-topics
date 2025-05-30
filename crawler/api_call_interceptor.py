from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.bidi.cdp import connect_cdp, connection_context, import_devtools, CdpConnection, CdpSession
from contextlib import asynccontextmanager
import json
import trio
import os
import shutil
from types import ModuleType
from api_call_collector import ApiCallCollector
from lib.db import db_connection

with open(os.path.dirname(os.path.realpath(__file__)) + "/intercept-api-calls.js") as file:
    INTERCEPT_CALLS_SCRIPT = file.read()

class APICallInterceptor:
    "An API Interceptor interacts with the browser (through the CDP protocol) and intercepts certain Browser API calls as either JavaScript calls or CDP events."

    driver: WebDriver
    script_loaded: bool
    collectors: list[ApiCallCollector]
    user_data_dir: str

    def __init__(self, driver: WebDriver, collectors: list[ApiCallCollector], user_data_dir: str = "~/.config/google-chrome"):
        self.driver = driver
        self.script_loaded = False
        self.collectors = collectors
        self.user_data_dir = os.path.expanduser(user_data_dir)

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

    async def _handle_target_created(self, event: any, conn: CdpConnection, devtools: ModuleType, nursery: trio.Nursery):
        """
        Event handler for the Target.targetCreated and Target.attachedToTarget events.
        Creates new sessions for each target discovered and initializes them.
        """
        assert isinstance(event, (devtools.target.TargetCreated, devtools.target.AttachedToTarget))
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

    async def _handle_binding_called(self, event, devtools: ModuleType):
        """
        Event handler for the Runtime.bindingCalled event.
        """
        assert isinstance(event, devtools.runtime.BindingCalled)
        if event.name == "calledAPIEvent":
            for collector in self.collectors:
                payload = json.loads(event.payload)
                if payload["description"] in collector.js_calls_to_listen:
                    await collector.handle_js_call(payload)

    async def _handle_cdp_events(self, session: CdpSession, conn: CdpConnection, devtools: ModuleType, nursery: trio.Nursery):
        """
        Event handler for the CDP events.
        """
        main_events = [devtools.runtime.BindingCalled, devtools.target.TargetCreated, devtools.target.AttachedToTarget]
        collector_events = [event_type for collector in self.collectors for event_type in collector.cdp_events_to_listen]
        events_to_listen = set(main_events + collector_events)
        async for event in session.listen(*events_to_listen):
            # Handle BindingCalled events
            if isinstance(event, devtools.runtime.BindingCalled):
                nursery.start_soon(self._handle_binding_called, event, devtools)
                # await self._handle_binding_called(event, devtools)

            # Handle TargetCreated and AttachedToTarget events
            if isinstance(event, (devtools.target.TargetCreated, devtools.target.AttachedToTarget)):
                nursery.start_soon(self._handle_target_created, event, conn, devtools, nursery)
                # await self._handle_target_created(event, conn, devtools, nursery)

            # Handle events for each collector
            for collector in self.collectors:
                if len(collector.cdp_events_to_listen) > 0 and isinstance(event, tuple(collector.cdp_events_to_listen)):
                    nursery.start_soon(collector.handle_cdp_event, event)
                    # await collector.handle_cdp_event(event)

    async def _handle_execution_contexts(self, session: CdpSession, devtools: ModuleType):
        """
        Handles the Runtime.executionContextCreated event to initialize collectors for each execution context.
        """
        async for event in session.listen(devtools.runtime.ExecutionContextCreated):
            await session.execute(devtools.runtime.evaluate(expression=INTERCEPT_CALLS_SCRIPT, context_id=event.context.id_))

    async def _init_session(self, conn: CdpConnection, session: CdpSession, devtools: ModuleType, nursery: trio.Nursery, target_type = "unknown"):
        """
        Performs the preliminary steps to track function calls within the given session
        """
        # Auto-attach to new targets and wait for debugger on start: this is to allow captuing all information
        await session.execute(devtools.target.set_auto_attach(auto_attach=True, wait_for_debugger_on_start=True, flatten=True))

        # Start event listener tasks
        nursery.start_soon(self._handle_cdp_events, session, conn, devtools, nursery)

        # Add binding for recording API calls
        await session.execute(devtools.runtime.add_binding(name="calledAPIEvent"))
        
        if target_type in ["page", "iframe"]:
            # Enable page commands and event logging
            await session.execute(devtools.page.enable())

            # Inject 'intercept-functions.js' script on all new documents (pages and iframes)
            await session.execute(devtools.page.add_script_to_evaluate_on_new_document(source=INTERCEPT_CALLS_SCRIPT))
        else:
            # For service workers/worklets, execute the script as soon as an execution context is created
            nursery.start_soon(self._handle_execution_contexts, session, devtools)

        # Enable runtime event logging (needed for Runtime.bindingCalled event)
        await session.execute(devtools.runtime.enable())

        # Initialize collectors for session
        for collector in self.collectors:
            await collector.init(session)

        # Resume only after having initialized everything
        await session.execute(devtools.runtime.run_if_waiting_for_debugger())

    async def _read_from_db(self):
        """
        Reads data from the database for each collector for which a database name is specified.
        """
        for collector in self.collectors:
            if collector.db_name is not None:
                # Copy the database file to a temporary location to avoid locking issues
                real_db_path = f"{self.user_data_dir}/Default/{collector.db_name}"
                tmp_db_path = f"/tmp/{collector.db_name}"
                try:
                    shutil.copy(real_db_path, tmp_db_path)
                except FileNotFoundError as e:
                    # Database not found: skip reading from it
                    return

                with db_connection(tmp_db_path) as conn:
                    await collector.handle_db_connection(conn)
                os.remove(tmp_db_path)

    @asynccontextmanager
    async def intercept(self):
        """
        This async context manager intercepts select JavaScript API calls while the code inside the block executes.
        It does so by opening a CDP connection to the browser
        """
        async with trio.open_nursery() as nursery:
            async with self._open_cdp_session(nursery) as (conn, session, devtools): 
                # Update devtools object for collectors
                for collector in self.collectors:
                    collector.devtools = devtools

                # Initialize main session
                await self._init_session(conn, session, devtools, nursery, target_type="page")

                try:
                    yield conn, session, devtools
                finally:
                    # Extract data from databases
                    await self._read_from_db()
                    
                    # Stop nursery tasks
                    nursery.cancel_scope.cancel()

    def get_calls(self) -> dict:
        try:
            return {
                collector.name: {
                    "javascript_functions": collector.js_calls.copy(),
                    "cdp_events": [ e.to_json() for e in collector.cdp_events ],
                    "db_data": collector.db_data.copy() if collector.db_data is not None else None
                }
                for collector in self.collectors
            }
        except AttributeError:
            print("Warning: CDP Event does not have a to_json() function.")
    
    def clear_calls(self):
        for collector in self.collectors:
            collector.clear_calls()