from http.server import SimpleHTTPRequestHandler, HTTPServer
import argparse
from urllib.parse import urlparse
import json
import sqlite3
import sys
import traceback
import signal

parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int, default=8080)
parser.add_argument('--cache_db', type=str, default="cache.db")

globals().update(vars(parser.parse_args()))

class CacheHandler(SimpleHTTPRequestHandler):

    def send_json(self, obj: dict):
        self.send_response(200)
        self.send_header('content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode())

    def do_GET(self):
        query_params = dict(qc.split("=") for qc in urlparse(self.path).query.split("&"))
        domain = query_params.get("domain")
        if domain is None:
            self.send_response(400)
            self.end_headers()
            return
        
        cached_result = get_attestation_result(domain)
        if cached_result is None:
            self.send_response(404)
            self.end_headers()
        else:
            self.send_json(cached_result)

    def do_POST(self):
        ctype = self.headers.get("content-type")
        if ctype != 'application/json':
            self.send_response(400)
            self.end_headers()
            return

        length = int(self.headers.get('content-length'))
        try:
            body = json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            return

        domain = body.get("domain")
        attested = body.get("attested")
        attestation_result = body.get("attestation_result")

        if domain is None or attested is None:
            self.send_response(400)
            self.end_headers()
            return
        
        if attested and attestation_result is None:
            self.send_response(400)
            self.end_headers()
            return
        
        save_attestation_result(domain, attested, attestation_result)

        self.send_response(201)
        self.end_headers()

def get_attestation_result(domain):
    sql =  "SELECT attested, attestation_result\
            FROM cache\
            WHERE domain = ?"
    result = db_conn.execute(sql, [domain]).fetchone()
    if result is None:
        return None
    attested, attestation_result = result
    if attestation_result is not None and len(attestation_result) > 0:
        attestation_result = json.loads(attestation_result)
    return { "attested": bool(attested), "attestation_result": attestation_result }

def save_attestation_result(domain, attested, attestation_result):
    sql =  "INSERT OR REPLACE INTO cache(domain, attested, attestation_result)\
            VALUES(?,?,?)"
    db_conn.execute(sql, [domain, attested, json.dumps(attestation_result)])

def init_database():
    sql =  "CREATE TABLE IF NOT EXISTS cache(\
                domain TEXT PRIMARY KEY,\
                attested INTEGER NOT NULL,\
                attestation_result TEXT)"
    db_conn.execute(sql)
    

if __name__ == '__main__':
    # Load from existing cache file, if it exists
    global db_conn
    db_conn = sqlite3.connect(cache_db)
    init_database()

    try:
        # Serve HTTP requests
        with HTTPServer(("", port), CacheHandler) as server:
            print("Server listening on port {}".format(port))
            server.serve_forever()
    except KeyboardInterrupt:
        print("Stopped")
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print("Exception at line {}: {}".format(exc_tb.tb_lineno, e))
        traceback.print_exception(exc_type, exc_obj, exc_tb)
    finally:
        db_conn.commit()
        db_conn.close()

def handle_sigterm(*args):
    print("Stopped")
    if db_conn:
        db_conn.commit()
        db_conn.close()

signal.signal(signal.SIGTERM, handle_sigterm)