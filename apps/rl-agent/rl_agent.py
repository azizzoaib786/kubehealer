# rl_agent.py — RL agent with masking, cooldowns, quorum-aware ML, fanout resets
#               + scale_up allowed during flagged breaches (if p95 > SLO)
#               + hysteretic scale_down when stably healthy (DOWN_P95_THRESH / STABLE_OK_TICKS)
import os, time, json, logging
import numpy as np
import requests
from kubernetes import client, config
from collections import defaultdict
from prometheus_client import Counter, Gauge, start_http_server

# Config (env)
PROM_URL       = os.getenv("PROM_URL", "http://prometheus-operated:9090")
NAMESPACE      = os.getenv("TARGET_NAMESPACE", "kubehealer")
DEPLOYMENT     = os.getenv("TARGET_DEPLOYMENT", "etl-sim")
ETL_ACT_URL    = os.getenv("ETL_ACT_URL", f"http://{DEPLOYMENT}.{NAMESPACE}.svc:8080")

P95_SLO        = float(os.getenv("P95_SLO", "2.0"))
FAIL_SLO       = float(os.getenv("FAIL_SLO", "0.01"))
SLOW_SLO       = float(os.getenv("SLOW_SLO", "0.02"))
SCALE_P95_THRESH = float(os.getenv("SCALE_P95_THRESH", str(P95_SLO)))  # breach gate for scale_up

MIN_R          = int(os.getenv("MIN_REPLICAS", "1"))
MAX_R          = int(os.getenv("MAX_REPLICAS", "4"))

TICK_S         = int(os.getenv("TICK_SECS", "30"))
METRICS_PORT   = int(os.getenv("METRICS_PORT", "8000"))

COOLDOWN_SCALE = int(os.getenv("COOLDOWN_SCALE_SECS", "30"))
COOLDOWN_ACT   = int(os.getenv("COOLDOWN_ACT_SECS", "15"))
RESET_TTL      = int(os.getenv("RESET_TTL_SECS", "180"))

LOG_LEVEL      = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT     = os.getenv("LOG_FORMAT", "json")  # json | plain

ENABLE_MASKING = os.getenv("ENABLE_MASKING", "1") == "1"
ENABLE_IMPUTE  = os.getenv("ENABLE_IMPUTE", "0") == "1"

IMPROV_BONUS   = float(os.getenv("IMPROVEMENT_BONUS", "0.0"))
HEAL_BONUS     = float(os.getenv("HEAL_BONUS", "0.6"))

# Fan-out resets to every ETL pod (clear sticky flags)
FANOUT_ALL_PODS = os.getenv("FANOUT_ALL_PODS", "1") == "1"
# Allow scale_up even if ETL/ML flags are set, when p95 > SLO
ALLOW_SCALE_ON_FLAGS = os.getenv("ALLOW_SCALE_ON_FLAGS", "1") == "1"

# NEW: predictable shrink-back
DOWN_P95_THRESH = float(os.getenv("DOWN_P95_THRESH", str(P95_SLO - 0.05)))  # e.g. 1.95 if SLO=2.0
STABLE_OK_TICKS = int(os.getenv("STABLE_OK_TICKS", "2"))
COST_WEIGHT     = float(os.getenv("COST_WEIGHT", "0.2"))

# Logging
def _setup_logger():
    log = logging.getLogger("kubehealer")
    log.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    h = logging.StreamHandler()
    if LOG_FORMAT == "json":
        class JsonFormatter(logging.Formatter):
            def format(self, record):
                base = {"ts": int(time.time()), "level": record.levelname.lower(),
                        "msg": record.getMessage(), "logger": record.name}
                kv = getattr(record, "kv", None)
                if isinstance(kv, dict): base.update(kv)
                return json.dumps(base, separators=(",",":"))
        h.setFormatter(JsonFormatter())
    else:
        h.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    log.handlers = [h]
    return log
log = _setup_logger()

# Prometheus metrics
ACTIONS = ["noop", "scale_up", "scale_down", "restart_one_pod", "reset_knobs"]
if ENABLE_IMPUTE:
    ACTIONS += ["impute_on", "impute_off"]

def A(name: str):
    return ACTIONS.index(name) if name in ACTIONS else None

action_total       = Counter("kubehealer_action_total", "Total actions taken", ["action"])
reward_gauge       = Gauge("kubehealer_reward", "Latest computed reward")
epsilon_gauge      = Gauge("kubehealer_epsilon", "Current epsilon")
replicas_gauge     = Gauge("kubehealer_target_replicas", "Current replicas")
tick_seconds       = Gauge("kubehealer_tick_seconds", "Tick interval seconds")
exception_total    = Counter("kubehealer_exceptions_total", "Exceptions caught", ["where"])
masked_total       = Counter("kubehealer_masked_total", "Times action masking applied", ["reason"])
heal_success_total = Counter("kubehealer_heal_success_total", "Times an action cleared a flag", ["action","flag"])
tick_seconds.set(TICK_S)

# PromQL helpers
def q(prom_url, expr):
    try:
        r = requests.get(f"{prom_url}/api/v1/query", params={"query": expr}, timeout=5)
        r.raise_for_status()
        res = r.json()["data"]["result"]
        return float(res[0]["value"][1]) if res else 0.0
    except Exception as e:
        exception_total.labels("prom_query").inc()
        log.warning("prom_query_error", extra={"kv":{"err":str(e), "expr":expr}})
        return 0.0

def read_signals(prom_url):
    # use ETL gauges for rates; smooth p95 over 30s; ML avg prob over 5m window
    return {
        "fail_rate":   q(prom_url, 'avg without (job,instance,endpoint,service,pod) (etl_fail_rate_observed)'),
        "slow_rate":   q(prom_url, 'avg without (job,instance,endpoint,service,pod) (etl_slow_rate_observed)'),
        "p95_latency": q(prom_url, 'histogram_quantile(0.95, sum by (le) (rate(etl_batch_latency_seconds_bucket[30s])))'),
        "throughput":  q(prom_url, 'sum(rate(etl_records_out_total[30s]))'),
        "ml_prob":     q(prom_url, 'avg_over_time(ml_anom_prob_avg_observed[5m])'),
        "etl_flag":    int(q(prom_url, 'max without (job,instance,endpoint,service,pod) (etl_anomaly_flag)')),
        "ml_flag":     int(q(prom_url, 'max without (job,instance,endpoint,service,pod) (ml_anomaly_flag)')),
    }

# Kubernetes helpers
def init_kube():
    try: config.load_incluster_config()
    except: config.load_kube_config()

def get_replicas(ns, deploy):
    api = client.AppsV1Api()
    sc = api.read_namespaced_deployment_scale(deploy, ns)
    return sc.spec.replicas

def set_replicas(ns, deploy, replicas):
    api = client.AppsV1Api()
    api.patch_namespaced_deployment_scale(deploy, ns, {"spec": {"replicas": replicas}})
    actual = api.read_namespaced_deployment_scale(deploy, ns).spec.replicas
    log.info("scaled", extra={"kv":{"deployment":deploy,"requested":replicas,"actual":actual}})
    return actual

def restart_one_pod(ns, deploy):
    core = client.CoreV1Api()
    pods = core.list_namespaced_pod(ns, label_selector=f'app={deploy}').items
    if not pods:
        log.warning("restart_one_pod_no_pods", extra={"kv":{"deployment":deploy}})
        return False
    pod = pods[0].metadata.name
    core.delete_namespaced_pod(pod, ns)
    log.info("restarted_pod", extra={"kv":{"pod":pod}})
    return True

# Actuator
def _post(path, params):
    url = f"{ETL_ACT_URL}{path}"
    try:
        r = requests.post(url, params=params, timeout=4)
        r.raise_for_status()
        return True
    except Exception as e:
        exception_total.labels("actuator").inc()
        log.warning("actuator_error", extra={"kv":{"url":url,"err":str(e)}})
        return False

# Fan-out helpers
def etl_pod_ips(ns, deploy):
    core = client.CoreV1Api()
    pods = core.list_namespaced_pod(ns, label_selector=f'app={deploy}').items
    return [p.status.pod_ip for p in pods if p.status and p.status.pod_ip]

def _post_host(host, path, params):
    url = f"http://{host}:8080{path}"
    try:
        r = requests.post(url, params=params, timeout=4)
        r.raise_for_status()
        return True
    except Exception as e:
        exception_total.labels("actuator").inc()
        log.warning("actuator_error", extra={"kv":{"url":url,"err":str(e)}})
        return False

def etl_reset_knobs():
    if FANOUT_ALL_PODS:
        ips = etl_pod_ips(NAMESPACE, DEPLOYMENT)
        oks = []
        for ip in ips:
            ok1 = _post_host(ip, "/act/fail_rate", {"value": 0})
            ok2 = _post_host(ip, "/act/slow", {"rate": 0, "ms": 0})
            oks.append(ok1 and ok2)
        all_ok = all(oks) if oks else False
        log.info("reset_knobs", extra={"kv":{"ok":all_ok,"fanout":len(ips)}})
        return all_ok
    ok1 = _post("/act/fail_rate", {"value": 0})
    ok2 = _post("/act/slow", {"rate": 0, "ms": 0})
    log.info("reset_knobs", extra={"kv":{"ok_fail_rate":ok1,"ok_slow":ok2,"fanout":0}})
    return ok1 and ok2

def etl_impute(on=True):
    if not ENABLE_IMPUTE: return False
    ok = _post("/act/impute", {"on": 1 if on else 0})
    log.info("impute_toggle", extra={"kv":{"on":bool(on),"ok":ok}})
    return ok

# RL core
class QAgent:
    def __init__(self, n_actions, alpha=0.4, gamma=0.95, eps=0.2, eps_min=0.05, eps_decay=0.999):
        self.Q = defaultdict(lambda: np.zeros(n_actions, dtype=np.float32))
        self.alpha, self.gamma = alpha, gamma
        self.eps, self.eps_min, self.eps_decay = eps, eps_min, eps_decay
        self.n_actions = n_actions
    def act(self, s):
        if np.random.rand() < self.eps: return np.random.randint(self.n_actions)
        return int(np.argmax(self.Q[s]))
    def learn(self, s, a, r, s2):
        q = self.Q[s][a]
        td = r + self.gamma * np.max(self.Q[s2]) - q
        self.Q[s][a] += self.alpha * td
        self.eps = max(self.eps_min, self.eps * self.eps_decay)
        epsilon_gauge.set(self.eps)

# State / Reward
def discretize(sig, replicas):
    return (
        int(sig["fail_rate"] > FAIL_SLO),
        int(sig["slow_rate"] > SLOW_SLO),
        int(sig["p95_latency"] > P95_SLO),
        int(sig["ml_prob"] > 0.5),
        min(max(replicas, MIN_R), MAX_R),
        int(bool(sig["etl_flag"] or sig["ml_flag"])),
    )

def reward(sig, replicas, prev_p95=None):
    r  = 1.0 * (1 if sig["p95_latency"] < P95_SLO else -1)
    r += 0.5 * (1 if sig["fail_rate"]  < FAIL_SLO else -1)
    r += 0.2 * (1 if sig["slow_rate"]  < SLOW_SLO else -1)
    r -= COST_WEIGHT * (replicas - MIN_R) / max(1, (MAX_R - MIN_R))
    r -= 1.0 * (sig["etl_flag"] or sig["ml_flag"])
    if IMPROV_BONUS and prev_p95 is not None:
        r += IMPROV_BONUS * (prev_p95 - sig["p95_latency"])
    return r

def reward_parts(sig, replicas):
    return {
        "p95":  1.0 * (1 if sig["p95_latency"] < P95_SLO else -1),
        "fail": 0.5 * (1 if sig["fail_rate"]  < FAIL_SLO else -1),
        "slow": 0.2 * (1 if sig["slow_rate"]  < SLOW_SLO else -1),
        "cost": -COST_WEIGHT * (replicas - MIN_R) / max(1, (MAX_R - MIN_R)),
        "flag": -1.0 * (sig["etl_flag"] or sig["ml_flag"]),
    }

# Actions
def apply_action(a, replicas, now, last_scale_ts, last_act_ts):
    did = False
    did_reset = False
    # respect cooldowns
    if a in (A("scale_up"), A("scale_down")) and (now - last_scale_ts) < COOLDOWN_SCALE:
        action_total.labels("noop").inc(); return replicas, last_scale_ts, last_act_ts, False, False
    if a in filter(lambda x: x is not None, [A("reset_knobs"), A("impute_on"), A("impute_off")]) and (now - last_act_ts) < COOLDOWN_ACT:
        action_total.labels("noop").inc(); return replicas, last_scale_ts, last_act_ts, False, False

    if a == A("scale_up") and replicas < MAX_R:
        replicas = set_replicas(NAMESPACE, DEPLOYMENT, replicas + 1)
        action_total.labels("scale_up").inc(); did = True; last_scale_ts = now
    elif a == A("scale_down") and replicas > MIN_R:
        replicas = set_replicas(NAMESPACE, DEPLOYMENT, replicas - 1)
        action_total.labels("scale_down").inc(); did = True; last_scale_ts = now
    elif a == A("restart_one_pod"):
        if restart_one_pod(NAMESPACE, DEPLOYMENT):
            action_total.labels("restart_one_pod").inc(); did = True
    elif a == A("reset_knobs"):
        if etl_reset_knobs():
            action_total.labels("reset_knobs").inc(); did = True; last_act_ts = now; did_reset = True
    elif ENABLE_IMPUTE and a == A("impute_on"):
        if etl_impute(True):
            action_total.labels("impute_on").inc(); did = True; last_act_ts = now
    elif ENABLE_IMPUTE and a == A("impute_off"):
        if etl_impute(False):
            action_total.labels("impute_off").inc(); did = True; last_act_ts = now
    else:
        action_total.labels("noop").inc()
    return replicas, last_scale_ts, last_act_ts, did, did_reset

def choose_masked_action(agent, s, mask: set | None):
    if not mask: return agent.act(s)
    if np.random.rand() < agent.eps: return int(np.random.choice(list(mask)))
    q = agent.Q[s]; return int(max(mask, key=lambda i: q[i]))

# Main
def main():
    start_http_server(METRICS_PORT)
    init_kube()
    agent = QAgent(n_actions=len(ACTIONS))
    s = None
    last_scale_ts = 0.0
    last_act_ts   = 0.0
    last_reset_ts = 0.0
    prev_p95 = None
    stable_ok = 0  # NEW: consecutive healthy ticks

    log.info("boot", extra={"kv":{
        "prom_url":PROM_URL, "namespace":NAMESPACE, "deployment":DEPLOYMENT,
        "etl_act_url":ETL_ACT_URL, "tick_secs":TICK_S,
        "cooldown":{"scale":COOLDOWN_SCALE,"act":COOLDOWN_ACT},
        "reset_ttl_secs": RESET_TTL,
        "slo":{"p95":P95_SLO,"fail":FAIL_SLO,"slow":SLOW_SLO},
        "replicas":{"min":MIN_R,"max":MAX_R},
        "masking": ENABLE_MASKING, "impute_enabled": ENABLE_IMPUTE,
        "fanout_all_pods": FANOUT_ALL_PODS,
        "allow_scale_on_flags": ALLOW_SCALE_ON_FLAGS,
        "down_p95_thresh": DOWN_P95_THRESH, "stable_ok_ticks": STABLE_OK_TICKS,
        "cost_weight": COST_WEIGHT,
    }})

    while True:
        try:
            sig = read_signals(PROM_URL)
            replicas = get_replicas(NAMESPACE, DEPLOYMENT)
            replicas_gauge.set(replicas)
            s2 = discretize(sig, replicas)
            if s is None: s = s2

            # update healthy streak
            if sig["p95_latency"] <= DOWN_P95_THRESH and sig["etl_flag"] == 0 and sig["ml_flag"] == 0:
                stable_ok += 1
            else:
                stable_ok = 0

            # masking (shielded RL)
            mask = None; reason = None; now = time.time()
            if ENABLE_MASKING:
                etl, ml, p95 = sig["etl_flag"], sig["ml_flag"], sig["p95_latency"]

                if stable_ok >= STABLE_OK_TICKS and replicas > MIN_R:
                    mask = {i for i in [A("scale_down"), A("noop")] if i is not None}
                    reason = "stable_below_slo"

                elif etl and not ml and p95 <= P95_SLO:
                    mask = {i for i in [A("restart_one_pod"), A("noop")] if i is not None}
                    reason = "etl_only_ok_latency"

                elif etl or ml:
                    allowed = {A("restart_one_pod"), A("noop")}
                    if (now - last_reset_ts) > RESET_TTL or p95 > P95_SLO:
                        allowed.add(A("reset_knobs"))
                    if ALLOW_SCALE_ON_FLAGS and p95 > P95_SLO:
                        allowed.add(A("scale_up"))
                    mask = {i for i in allowed if i is not None}
                    reason = "anomaly_flags"

                elif p95 > SCALE_P95_THRESH:
                    mask = {i for i in [A("scale_up"), A("reset_knobs"), A("noop")] if i is not None}
                    reason = "latency_breach"

                # enforce bounds
                if replicas >= MAX_R and mask: mask.discard(A("scale_up"))
                if replicas <= MIN_R and mask: mask.discard(A("scale_down"))
                if mask is not None:
                    masked_total.labels(reason or "generic").inc()

            a = choose_masked_action(agent, s2, mask)

            prev_etl_flag = sig["etl_flag"]; prev_ml_flag = sig["ml_flag"]
            new_r, last_scale_ts, last_act_ts, did, did_reset = apply_action(a, replicas, now, last_scale_ts, last_act_ts)
            if did_reset: last_reset_ts = now

            time.sleep(TICK_S)

            sig2 = read_signals(PROM_URL)
            r = reward(sig2, new_r, prev_p95=prev_p95)
            if prev_etl_flag == 1 and sig2["etl_flag"] == 0:
                r += HEAL_BONUS; heal_success_total.labels(ACTIONS[a], "etl").inc()
            if prev_ml_flag == 1 and sig2["ml_flag"] == 0:
                r += HEAL_BONUS; heal_success_total.labels(ACTIONS[a], "ml").inc()

            reward_gauge.set(r); prev_p95 = sig2["p95_latency"]
            s3 = discretize(sig2, new_r); agent.learn(s2, a, r, s3); s = s3

            parts = reward_parts(sig2, new_r)
            log.info("decision", extra={"kv":{
                "action":ACTIONS[a],
                "masked": bool(mask is not None),
                "mask_reason": reason,
                "allowed_actions": [ACTIONS[i] for i in sorted(mask)] if mask else None,
                "did_act":bool(did),
                "reward":round(r,4), "epsilon":round(agent.eps,4),
                "replicas":new_r, "stable_ok_ticks": stable_ok,
                "signals":{"p95":sig2["p95_latency"],
                           "fail":sig2["fail_rate"],
                           "slow":sig2["slow_rate"],
                           "ml_prob":sig2["ml_prob"],
                           "flags":{"etl":sig2["etl_flag"],"ml":sig2["ml_flag"]}},
                "reward_parts":parts
            }})
        except Exception:
            exception_total.labels("main_loop").inc()
            log.exception("loop_exception")
            time.sleep(TICK_S)

if __name__ == "__main__":
    main()
