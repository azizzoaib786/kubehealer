#!/usr/bin/env python3
# etl_sim_lite.py — minimal ETL sim for ML/RL demos (sticky-flag fix + warmup)
import os, json, time, random, threading, signal
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from prometheus_client import start_http_server, Counter, Gauge, Histogram

# helpers
def _as_int(n, d):
    try: return int(os.getenv(n, str(d)))
    except: return d
def _as_float(n, d):
    try: return float(os.getenv(n, str(d)))
    except: return d
def _clamp01(x):
    try:
        x = float(x); return max(0.0, min(1.0, x))
    except:
        return 0.0

# config (tiny)
APP_NAME = os.getenv("APP_NAME","etl-sim-lite")
METRICS_PORT = _as_int("METRICS_PORT", 8000)
BATCH_SIZE = max(1, _as_int("BATCH_SIZE", 50))
WORK_INTERVAL_SEC = _as_float("WORK_INTERVAL_SEC", 0.02)
LOG_JSON = os.getenv("LOG_JSON","true").lower()=="true"

# legacy/system chaos
FAIL_RATE = _clamp01(os.getenv("FAIL_RATE","0.02"))
SLOW_RATE = _clamp01(os.getenv("SLOW_RATE","0.05"))
SLOW_MS   = _as_int("SLOW_MS", 1200)

# anomaly thresholds (unchanged) + new knobs
ANOMALY_FAIL_THRESH = _as_float("ANOMALY_FAIL_THRESH", 0.05)
ANOMALY_SLOW_THRESH = _as_float("ANOMALY_SLOW_THRESH", 0.10)
ANOMALY_ANOM_RATE_THRESH = _as_float("ANOMALY_ANOM_RATE_THRESH", 0.10)  # NEW: rate-based
ANOMALY_CLEAR_WINDOWS = _as_int("ANOMALY_CLEAR_WINDOWS", 2)

# warmup + data sufficiency
STARTUP_GRACE_SEC = _as_int("STARTUP_GRACE_SEC", 60)   # NEW: ignore early windows
MIN_WINDOW_RECORDS = _as_int("MIN_WINDOW_RECORDS", 100) # NEW: need enough samples

CITY_NAME = os.getenv("CITY_NAME", "dubai")

# simple data anomaly: temperature z-score
TEMP_SIGMA = _as_float("WEATHER_TEMP_SIGMA_C", 3.0)
TEMP_Z_THRESH = _as_float("WEATHER_TEMP_Z_THRESH", 3.0)
HEATWAVE_DELTA_C = _as_float("WEATHER_HEATWAVE_DELTA_C", 0.0)

# optional MinIO sink (disabled by default)
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT","").strip()
MINIO_ENABLED = bool(MINIO_ENDPOINT)
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY","")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY","")
MINIO_BUCKET     = os.getenv("MINIO_BUCKET","etl-bucket")
MINIO_SECURE     = os.getenv("MINIO_SECURE","false").lower()=="true"
MINIO_PREFIX     = os.getenv("MINIO_PREFIX","events")

# metrics
RECORDS_IN   = Counter("etl_records_in_total",  "Total records in")
RECORDS_OUT  = Counter("etl_records_out_total", "Total records out")
RECORDS_FAIL = Counter("etl_records_failed_total","Total records failed")
# Extended buckets so p95 can exceed 5s if needed
BATCH_LAT    = Histogram("etl_batch_latency_seconds","Batch latency (s)", buckets=(0.05,0.2,0.5,1,2,5,10,20))
FAIL_RATE_OBS= Gauge("etl_fail_rate_observed","Observed fail rate in window")
SLOW_RATE_OBS= Gauge("etl_slow_rate_observed","Observed slow rate in window")
TEMP_Z_MAX   = Gauge("weather_temp_z_max","Max |z| temp in window")
WEATHER_ANOM_RATE = Gauge("weather_anom_rate_observed","Fraction anomalous records")
ANOMALY_FLAG = Gauge("etl_anomaly_flag","1=anomaly,0=normal")
HEALTH_STATUS= Gauge("etl_health_status","1=up,0=down")
MINIO_WRITES = Counter("etl_minio_writes_total","Total MinIO object writes")

# per-window raw counts (unchanged)
WINDOW_IN   = Gauge("etl_window_records_in", "Records seen in last heartbeat window")
WINDOW_FAIL = Gauge("etl_window_records_failed", "Failed records in last heartbeat window")

# state
_obs_in=_obs_fail=_obs_slow=0
_w_obs=_w_anom=0
_w_zmax=0.0
_recent_ok=[]
_anom_latched=False

def log(msg, **kw):
    if LOG_JSON:
        out={"ts":datetime.now(timezone.utc).isoformat(),"app":APP_NAME,"msg":msg}; out.update(kw)
        print(json.dumps(out), flush=True)
    else:
        print(f"[{APP_NAME}] {msg} " + " ".join(f"{k}={v}" for k,v in kw.items()), flush=True)

# simple temperature baseline: seasonal + diurnal (compact)
def _expected_temp(dt):
    doy = dt.timetuple().tm_yday
    season = 30.0 + 10.0 * __import__("math").sin(2*__import__("math").pi*(doy-200)/365.0)
    hour = dt.hour + dt.minute/60.0
    diurnal = 6.0 * __import__("math").sin(2*__import__("math").pi*(hour-15)/24.0)
    return season + diurnal + HEATWAVE_DELTA_C

def _event():
    now = datetime.now(timezone.utc)
    exp = _expected_temp(now)
    temp = random.gauss(exp, TEMP_SIGMA)
    z = (temp-exp)/max(0.001, TEMP_SIGMA)
    return {
        "ts": now.isoformat(),
        "city": CITY_NAME,
        "temp_c": round(temp,2),
        "expected_temp_c": round(exp,2),
        "z_temp": round(z,3)
    }

# HTTP control
class Handler(BaseHTTPRequestHandler):
    def _ok(self, data):
        b=json.dumps(data).encode()
        self.send_response(200); self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if self.path=="/healthz":
            self.send_response(200); self.end_headers(); self.wfile.write(b"ok"); return
        self.send_response(200); self.end_headers(); self.wfile.write(b"etl-sim-lite")
    def do_POST(self):
        global FAIL_RATE,SLOW_RATE,SLOW_MS,HEATWAVE_DELTA_C,_anom_latched,_recent_ok
        from urllib.parse import urlparse, parse_qs
        p=urlparse(self.path); q={k:v[0] for k,v in parse_qs(p.query).items()}
        try:
            if p.path=="/act/fail_rate":
                FAIL_RATE=_clamp01(q.get("value","0.02")); return self._ok({"ok":True,"fail_rate":FAIL_RATE})
            if p.path=="/act/slow":
                SLOW_RATE=_clamp01(q.get("rate","0.05")); SLOW_MS=max(0,int(q.get("ms","1200")))
                return self._ok({"ok":True,"slow_rate":SLOW_RATE,"slow_ms":SLOW_MS})
            if p.path=="/act/weather":
                HEATWAVE_DELTA_C=float(q.get("delta","0")); return self._ok({"ok":True,"heatwave_delta_c":HEATWAVE_DELTA_C})
            if p.path=="/act/anomaly":
                # Backward compatible clear; optional ?set=1 to force a demo anomaly
                if q.get("set","0") in ("1","true","True"):
                    _anom_latched=True; _recent_ok.clear(); ANOMALY_FLAG.set(1); return self._ok({"ok":True,"anomaly":1})
                _anom_latched=False; _recent_ok.clear(); ANOMALY_FLAG.set(0); return self._ok({"ok":True,"anomaly":0})
            self.send_response(404); self.end_headers()
        except Exception as ex:
            self.send_response(400); self.end_headers(); self.wfile.write(json.dumps({"error":str(ex)}).encode())
    def log_message(self,*_): return

def _start_http():
    HTTPServer(("0.0.0.0",8080),Handler).serve_forever()

_stop=threading.Event()
def _sig(*_): log("sigterm"); _stop.set()
signal.signal(signal.SIGTERM,_sig); signal.signal(signal.SIGINT,_sig)

# MinIO (optional)
_minio = None
def _init_minio():
    global _minio
    if not MINIO_ENABLED: return
    try:
        from minio import Minio
        _minio = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY, secret_key=MINIO_SECRET_KEY, secure=MINIO_SECURE)
        try:
            if not _minio.bucket_exists(MINIO_BUCKET):
                _minio.make_bucket(MINIO_BUCKET)
        except Exception:
            pass
        log("minio_ready", endpoint=MINIO_ENDPOINT, bucket=MINIO_BUCKET)
    except Exception as ex:
        log("minio_error", error=str(ex)); _minio=None

def _write_minio(batch):
    if not _minio or not batch: return
    key = f"{MINIO_PREFIX}/{datetime.now(timezone.utc):%Y/%m/%d/%H}/weather-{int(time.time())}.jsonl"
    payload = ("\n".join(json.dumps(x) for x in batch)).encode()
    _minio.put_object(MINIO_BUCKET, key, data=__import__("io").BytesIO(payload), length=len(payload))
    MINIO_WRITES.inc()
    log("minio_write", key=key, count=len(batch))

# main
def run():
    global _obs_in,_obs_fail,_obs_slow,_w_obs,_w_anom,_w_zmax,_anom_latched,_recent_ok
    threading.Thread(target=_start_http, daemon=True).start()
    start_http_server(METRICS_PORT); HEALTH_STATUS.set(1)
    _init_minio()
    _start_ts = time.time()
    last_hb=time.time()
    try:
        while not _stop.is_set():
            t0=time.time(); batch=[]
            while len(batch)<BATCH_SIZE and not _stop.is_set():
                slow = random.random()<SLOW_RATE
                fail = random.random()<FAIL_RATE
                if slow:
                    _obs_slow+=1; time.sleep(SLOW_MS/1000.0)
                ev=_event(); _obs_in+=1; RECORDS_IN.inc()
                if fail:
                    _obs_fail+=1; RECORDS_FAIL.inc()
                else:
                    is_anom = abs(ev["z_temp"])>TEMP_Z_THRESH
                    ev["anomaly"]=is_anom
                    _w_obs+=1; _w_zmax=max(_w_zmax, abs(ev["z_temp"]))
                    if is_anom: _w_anom+=1
                    batch.append(ev)
                time.sleep(WORK_INTERVAL_SEC)
            # emit
            RECORDS_OUT.inc(len(batch))
            if MINIO_ENABLED:
                try: _write_minio(batch)
                except Exception as ex: log("minio_write_error", error=str(ex), batch_len=len(batch))
            batch.clear()
            BATCH_LAT.observe(time.time()-t0)

            # heartbeat ~10s
            if time.time()-last_hb>10:
                last_hb=time.time()
                fail_obs = (_obs_fail/_obs_in) if _obs_in else 0.0
                slow_obs = (_obs_slow/_obs_in) if _obs_in else 0.0
                anom_rate = (_w_anom/_w_obs) if _w_obs else 0.0

                # set gauges for rates + window counts
                FAIL_RATE_OBS.set(fail_obs)
                SLOW_RATE_OBS.set(slow_obs)
                TEMP_Z_MAX.set(_w_zmax)
                WEATHER_ANOM_RATE.set(anom_rate)
                WINDOW_IN.set(_obs_in)
                WINDOW_FAIL.set(_obs_fail)

                # anomaly latch logic (window-based; ignore max-z spikes; add warm-up & min-size)
                uptime = time.time() - _start_ts
                enough_data = (_obs_in >= MIN_WINDOW_RECORDS)
                can_evaluate = (uptime >= STARTUP_GRACE_SEC) and enough_data

                trigger = can_evaluate and (
                    (fail_obs >= ANOMALY_FAIL_THRESH) or
                    (slow_obs >= ANOMALY_SLOW_THRESH) or
                    (anom_rate >= ANOMALY_ANOM_RATE_THRESH)
                )

                if trigger:
                    _anom_latched=True; _recent_ok.clear()
                else:
                    ok_window = (
                        (fail_obs < 0.5*ANOMALY_FAIL_THRESH) and
                        (slow_obs < 0.5*ANOMALY_SLOW_THRESH) and
                        (anom_rate < 0.5*ANOMALY_ANOM_RATE_THRESH)
                    )
                    _recent_ok.append(1 if ok_window else 0)
                    if len(_recent_ok) > ANOMALY_CLEAR_WINDOWS:
                        _recent_ok = _recent_ok[-ANOMALY_CLEAR_WINDOWS:]
                    if len(_recent_ok) >= ANOMALY_CLEAR_WINDOWS and all(_recent_ok):
                        _anom_latched=False; _recent_ok.clear()

                ANOMALY_FLAG.set(1 if _anom_latched else 0)

                # include raw counts in the log for transparency
                log("heartbeat",
                    window_in=_obs_in,
                    window_fail=_obs_fail,
                    fail_rate_obs=round(fail_obs,4),
                    slow_rate_obs=round(slow_obs,4),
                    temp_z_max=round(_w_zmax,3),
                    anom_rate=round(anom_rate,4),
                    anomaly=_anom_latched,
                    can_eval=can_evaluate,
                    uptime=int(uptime))

                # reset window counters
                _obs_in=_obs_fail=_obs_slow=0
                _w_obs=_w_anom=0
                _w_zmax=0.0
    finally:
        HEALTH_STATUS.set(0); log("stopped")

if __name__=="__main__":
    run()