from selenium.webdriver.common.bidi.cdp import CdpSession
from api_call_collector import ApiCallCollector
from types import ModuleType
from lib.db import DBConnection
from api_collectors.proto import aggregatable_report_pb2
from google.protobuf.json_format import MessageToDict

class PrivateAggregationApiCallCollector(ApiCallCollector):
    """
    Saves calls related to the Private Aggregation API.

    Types of calls registered so far:
    - Aggregatable reports saved in the AggregationService database.
    """

    last_report_request_time: int
    
    def __init__(self):
        super().__init__()
        self.name = "private_aggregation"
        self.js_calls_to_listen = [
            # No JS calls
        ]
        self.db_name = "AggregationService"
        self.db_data = []
        self.last_report_request_time = 0

    def _set_devtools(self, devtools: ModuleType):
        self.cdp_events_to_listen = [
            # No CDP Events
        ]
        self._devtools = devtools

    async def init(self, session: CdpSession):
        # Do nothing
        return

    async def handle_js_call(self, payload: dict):
        self.register_js_call(payload)

    async def handle_cdp_event(self, event):
        self.register_cdp_event(event)

    async def handle_db_connection(self, conn: DBConnection):
        data = []
        cur = conn.cursor()
        res = cur.execute("""
            SELECT creation_time, reporting_origin, request_proto FROM report_requests
            WHERE creation_time > ?
        """, [self.last_report_request_time])

        last_report_time = 0
        for creation_time, reporting_origin, request_proto in res.fetchall():
            # Convert the request_proto from bytes to a protobuf object
            report_req_proto = aggregatable_report_pb2.AggregatableReportRequest()
            report_req_proto.ParseFromString(request_proto)

            data.append({
                "creation_time": creation_time,
                "reporting_origin": reporting_origin,
                "report_request": MessageToDict(report_req_proto)
            })

            if creation_time > last_report_time:
                last_report_time = creation_time

        self.db_data = data
        self.last_report_request_time = last_report_time