#!/usr/bin/env python3
# ml_scorer.py — trains & scores from MinIO, exports Prometheus metrics
# Adds: quorum gating + latched anomaly flag with clear-windows hysteresis.

import os, time, json, io
from datetime import datetime, timezone
from collections import deque

import ujson
import numpy as np
from minio import Minio
from sklearn.ensemble import IsolationForest
from prometheus_client import start_http_server, Gauge, Counter

APP = "ml-scorer"

# ---- env ----
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "")
MINIO_SECURE   = os.getenv("MINIO_SECURE", "false").lower() == "true"
MINIO_ACCESS   = os.getenv("MINIO_ACCESS_KEY", "")
MINIO_SECRET   = os.getenv("MINIO_SECRET_KEY", "")
MINIO_BUCKET   = os.getenv("MINIO_BUCKET", "etl-bucket")
EVENTS_PREFIX  = os.getenv("EVENTS_PREFIX", "events")
SCORES_PREFIX  = os.getenv("SCORES_PREFIX", "training-data/scores")
MODEL_PREFIX   = os.getenv("MODEL_PREFIX", "training-data/models")
CITY_FILTER    = os.getenv("CITY_FILTER", "")

POLL_SEC       = float(os.getenv("POLL_SEC", "10"))
MIN_FIT        = int(os.getenv("MIN_FIT", "500"))
MAX_BUF        = int(os.getenv("MAX_BUF", "10000"))
PROB_THRESH    = float(os.getenv("PROB_THRESH", "0.80"))
FRAC_THRESH    = float(os.getenv("FRAC_THRESH", "0.10"))   # kept for compat (not used for final flag)
METRICS_PORT   = int(os.getenv("METRICS_PORT", "9105"))

# Quorum controls for per-file decision
QUORUM_MIN_N   = int(os.getenv("QUORUM_MIN_N", "50"))
QUORUM_FRAC    = float(os.getenv("QUORUM_FRAC", "0.5"))

# Hysteresis for the *latched* ML flag
ML_ANOM_CLEAR_WINDOWS = int(os.getenv("ML_ANOM_CLEAR_WINDOWS", "2"))
ML_CLEAR_MULT         = float(os.getenv("ML_CLEAR_MULT", "0.6"))

# ---- metrics ----
PROB_AVG     = Gauge("ml_anom_prob_avg_observed", "avg ML anomaly prob in last scored file")
FRAC_FLAG    = Gauge("ml_frac_flagged_observed",  "fraction flagged (ML) in last scored file")
LAST_FILE_TS = Gauge("ml_last_file_unixts",       "unixtime of last scored file")
FILES_SCORED = Counter("ml_files_scored_total",   "files scored")
RECS_SCORED  = Counter("ml_records_scored_total", "records scored")

# model state + overall flag (unchanged names)
ML_MODEL_STATE  = Gauge("ml_model_state", "1=fitted,0=warmup")
ML_ANOMALY_FLAG = Gauge("ml_anomaly_flag", "1=ml anomaly ACTIVE (latched), else 0")

def log(msg, **kw):
    print(json.dumps({"ts": datetime.now(timezone.utc).isoformat(), "app": APP, "msg": msg, **kw}), flush=True)

def client():
    assert MINIO_ENDPOINT, "MINIO_ENDPOINT required"
    return Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS, secret_key=MINIO_SECRET, secure=MINIO_SECURE)

def latest_object(cli, prefix):
    latest = None
    for obj in cli.list_objects(MINIO_BUCKET, prefix=prefix, recursive=True):
        if latest is None or obj.last_modified > latest.last_modified:
            latest = obj
    return latest

def read_jsonl(cli, key):
    res = cli.get_object(MINIO_BUCKET, key)
    try:
        for chunk in res.stream(1024 * 1024):
            for line in chunk.splitlines():
                if line:
                    yield ujson.loads(line)
    finally:
        res.close(); res.release_conn()

def features(rec):
    # etl-sim-lite: ts, city, temp_c, expected_temp_c, z_temp, anomaly
    try:
        dt = float(rec.get("temp_c", 0.0)) - float(rec.get("expected_temp_c", 0.0))
        z  = float(rec.get("z_temp", 0.0))
        return np.array([dt, z], dtype=np.float32)
    except Exception:
        return None

def to_prob(scores):
    # Convert IsolationForest score_samples (higher = more normal) to [0..1] anomaly prob
    s = -scores
    lo, hi = np.percentile(s, 5), np.percentile(s, 95)
    if hi <= lo: hi = lo + 1e-6
    return np.clip((s - lo) / (hi - lo), 0.0, 1.0)

def run():
    cli = client()
    start_http_server(METRICS_PORT)

    # model starts in warmup
    ML_MODEL_STATE.set(0)

    buf = deque(maxlen=MAX_BUF)
    last_key = None
    clf = None

    # ---- latch state ----
    ml_latched = False
    clean_streak = 0

    while True:
        try:
            obj = latest_object(cli, EVENTS_PREFIX)
            if obj is None:
                log("no_objects_yet"); time.sleep(POLL_SEC); continue
            if obj.object_name == last_key:
                time.sleep(POLL_SEC); continue

            rows, feats = [], []
            for r in read_jsonl(cli, obj.object_name):
                if CITY_FILTER and r.get("city") != CITY_FILTER:
                    continue
                f = features(r)
                if f is None: continue
                rows.append(r); feats.append(f); buf.append(f)
            if not rows:
                last_key = obj.object_name
                continue

            Xbuf = np.vstack(buf) if len(buf) else np.vstack(feats)
            if clf is None and len(Xbuf) >= MIN_FIT:
                clf = IsolationForest(n_estimators=100, contamination="auto", random_state=42)
                clf.fit(Xbuf)
                ML_MODEL_STATE.set(1)  # flip to fitted
                log("model_fit", n=len(Xbuf))

            if clf is None:
                # warmup: use |z| scaled as a pseudo-prob
                probs  = np.clip(np.abs([r.get("z_temp", 0.0) for r in rows]) / 5.0, 0.0, 1.0)
                scores = -probs
                model_state = "warmup"
            else:
                scores = clf.score_samples(np.vstack(feats))
                probs  = to_prob(scores)
                model_state = "fitted"

            # per-record anomaly decisions from ML probability
            flags = probs > PROB_THRESH
            frac  = float(np.mean(flags))
            n_rec = len(rows)
            prob_avg = float(np.mean(probs))

            # Raw per-file ML decision via quorum
            ml_raw = (n_rec >= QUORUM_MIN_N) and (frac >= QUORUM_FRAC)

            # ---- latch + clear-windows hysteresis ----
            if not ml_latched:
                if ml_raw:
                    ml_latched = True
                    clean_streak = 0
            else:
                # Count a "clean" window if both fraction and prob_avg drop below relaxed thresholds
                clean_ok = (not ml_raw) and (frac < QUORUM_FRAC * ML_CLEAR_MULT) and (prob_avg < PROB_THRESH * ML_CLEAR_MULT)
                if clean_ok:
                    clean_streak += 1
                else:
                    clean_streak = 0
                if clean_streak >= ML_ANOMAL_CLEAR_WINDOWS:
                    ml_latched = False
                    clean_streak = 0

            ML_ANOMALY_FLAG.set(1.0 if ml_latched else 0.0)

            out_key = f"{SCORES_PREFIX}/{datetime.now(timezone.utc):%Y/%m/%d/%H}/scored-{int(time.time())}.jsonl"
            out_lines = []
            for r, p, s, fl in zip(rows, probs.tolist(), scores.tolist(), flags.tolist()):
                rr = dict(r)
                rr["anom_prob"]  = round(float(p), 4)
                rr["anom_score"] = round(float(s), 6)
                rr["ml_anomaly"] = bool(fl)
                out_lines.append(ujson.dumps(rr))
            payload = ("\n".join(out_lines)).encode()
            cli.put_object(MINIO_BUCKET, out_key, data=io.BytesIO(payload), length=len(payload))

            # metrics
            PROB_AVG.set(prob_avg)
            FRAC_FLAG.set(frac)
            LAST_FILE_TS.set(obj.last_modified.timestamp())
            FILES_SCORED.inc()
            RECS_SCORED.inc(n_rec)

            log("scored_file_written",
                in_key=obj.object_name, out_key=out_key, n=n_rec,
                prob_avg=round(prob_avg, 4),
                frac_flag=round(frac, 4), quorum_frac=QUORUM_FRAC, quorum_min_n=QUORUM_MIN_N,
                model_state=model_state, buf_n=len(buf),
                ml_anomaly_raw=ml_raw, ml_latched=ml_latched, clean_streak=clean_streak,
                clear_rule={"windows": ML_ANOM_CLEAR_WINDOWS, "mult": ML_CLEAR_MULT})

            last_key = obj.object_name
        except Exception as ex:
            log("error", error=str(ex))
            time.sleep(POLL_SEC)

if __name__ == "__main__":
    run()