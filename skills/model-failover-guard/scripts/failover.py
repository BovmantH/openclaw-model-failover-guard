#!/usr/bin/env python3
import json, os, subprocess, sys, time
from pathlib import Path

HOME = Path.home()
DEFAULT_OPENCLAW_CFG = HOME / '.openclaw' / 'openclaw.json'
DEFAULT_STATE = HOME / '.openclaw' / 'failover-state.json'
DEFAULT_LOG = HOME / '.openclaw' / 'failover.log'
LOCAL_CFG = Path(__file__).resolve().parent / 'config.json'


def expand(p: str) -> Path:
    return Path(os.path.expanduser(p)).resolve()


def load_runtime_config():
    cfg = {
        'configPath': str(DEFAULT_OPENCLAW_CFG),
        'statePath': str(DEFAULT_STATE),
        'logPath': str(DEFAULT_LOG),
        'primaryModel': '',
        'preferredFallbackProvider': '',
        'excludedProviders': [],
        'allowedFallbacks': [],
        'candidateProbe': {
            'enabled': True,
            'timeoutSec': 30,
        },
        'candidateCooldown': {
            'defaultSec': 600,
            'ban400Sec': 3600,
            'ban401Sec': 1800,
            'ban403Sec': 1800,
        },
        'failoverOnErrors': ['http_429', 'http_5xx', 'timeout', 'connection'],
        'failThreshold': 3,
        'recoverThreshold': 3,
        'checkIntervalSec': 300,
        'testTimeoutSec': 45,
    }
    if LOCAL_CFG.exists():
        try:
            file_cfg = json.loads(LOCAL_CFG.read_text(encoding='utf-8'))
            cfg.update(file_cfg)
        except Exception:
            pass

    cfg['CONFIG_PATH'] = expand(cfg['configPath'])
    cfg['STATE_PATH'] = expand(cfg['statePath'])
    cfg['LOG_PATH'] = expand(cfg['logPath'])
    cfg['FAIL_THRESHOLD'] = int(cfg['failThreshold'])
    cfg['RECOVER_THRESHOLD'] = int(cfg['recoverThreshold'])
    cfg['CHECK_INTERVAL_SEC'] = int(cfg['checkIntervalSec'])
    cfg['TEST_TIMEOUT_SEC'] = int(cfg['testTimeoutSec'])
    cfg['EXCLUDED_PROVIDERS'] = set(cfg.get('excludedProviders') or [])
    cfg['ALLOWED_FALLBACKS'] = [m for m in (cfg.get('allowedFallbacks') or []) if isinstance(m, str)]
    cfg['CANDIDATE_PROBE'] = cfg.get('candidateProbe') or {}
    cfg['CANDIDATE_COOLDOWN'] = cfg.get('candidateCooldown') or {}
    cfg['FAILOVER_ON_ERRORS'] = set(cfg.get('failoverOnErrors') or [])
    return cfg


R = load_runtime_config()


def log(msg: str):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line)
    R['LOG_PATH'].parent.mkdir(parents=True, exist_ok=True)
    with R['LOG_PATH'].open('a', encoding='utf-8') as f:
        f.write(line + '\n')


def load_state():
    if R['STATE_PATH'].exists():
        try:
            return json.loads(R['STATE_PATH'].read_text(encoding='utf-8'))
        except Exception:
            pass
    return {
        'consecutive_failures': 0,
        'consecutive_fallback_health': 0,
        'last_switch': None,
        'current_fallback': None,
        'candidate_health': {},
    }


def save_state(state):
    R['STATE_PATH'].parent.mkdir(parents=True, exist_ok=True)
    R['STATE_PATH'].write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')


def load_openclaw_config():
    return json.loads(R['CONFIG_PATH'].read_text(encoding='utf-8'))


def save_openclaw_config(cfg):
    R['CONFIG_PATH'].write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding='utf-8')


def _now_ts():
    return int(time.time())


def get_primary_model(cfg):
    return cfg.get('agents', {}).get('defaults', {}).get('model', {}).get('primary')


def set_primary_model(cfg, model_id: str):
    cfg.setdefault('agents', {}).setdefault('defaults', {}).setdefault('model', {})['primary'] = model_id


def list_configured_models(cfg):
    m = cfg.get('agents', {}).get('defaults', {}).get('models', {})
    models = [k for k in m.keys() if isinstance(k, str) and '/' in k]
    if models:
        return sorted(set(models))

    out = []
    providers = cfg.get('models', {}).get('providers', {})
    for provider, pdata in providers.items():
        for mm in pdata.get('models', []) or []:
            mid = mm.get('id')
            if mid:
                out.append(f'{provider}/{mid}')
    return sorted(set(out))


def get_target_primary(cfg):
    configured_primary = get_primary_model(cfg)
    return R['primaryModel'] or configured_primary


def rank_candidates(models):
    preferred = R.get('preferredFallbackProvider') or ''

    def rank(model_id: str):
        provider = model_id.split('/', 1)[0]
        pref_rank = 0 if (preferred and provider == preferred) else 1
        return (pref_rank, model_id)

    return sorted(models, key=rank)


def _classify_error(detail: str):
    d = (detail or '').lower()
    if 'timeout' in d or 'timed out' in d:
        return 'timeout'
    if 'connection' in d or 'conn' in d:
        return 'connection'
    if 'http 429' in d or '429' in d:
        return 'http_429'
    if 'http 401' in d or '401' in d:
        return 'http_401'
    if 'http 403' in d or '403' in d:
        return 'http_403'
    if 'http 400' in d or '400' in d:
        return 'http_400'
    if 'http 5' in d or ' 5' in d:
        return 'http_5xx'
    return 'unknown'


def _cooldown_for_error(err_type: str):
    cd = R.get('CANDIDATE_COOLDOWN') or {}
    if err_type == 'http_400':
        return int(cd.get('ban400Sec', 0) or 0)
    if err_type == 'http_401':
        return int(cd.get('ban401Sec', 0) or 0)
    if err_type == 'http_403':
        return int(cd.get('ban403Sec', 0) or 0)
    return int(cd.get('defaultSec', 0) or 0)


def _is_in_cooldown(state, model_id: str):
    h = (state.get('candidate_health') or {}).get(model_id) or {}
    until = h.get('cooldownUntil') or 0
    return until and _now_ts() < int(until)


def _mark_candidate_failure(state, model_id: str, err_type: str, detail: str):
    cd = _cooldown_for_error(err_type)
    health = state.setdefault('candidate_health', {})
    entry = health.setdefault(model_id, {})
    entry['lastErrorType'] = err_type
    entry['lastError'] = detail[-500:]
    entry['failCount'] = int(entry.get('failCount') or 0) + 1
    if cd > 0:
        entry['cooldownUntil'] = _now_ts() + cd


def test_current_default_model():
    cmd = [
        'openclaw', 'agent', '--agent', 'main',
        '--message', '只回复OK', '--json', '--timeout', str(R['TEST_TIMEOUT_SEC'])
    ]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=R['TEST_TIMEOUT_SEC'] + 20)
        out = (p.stdout or '') + '\n' + (p.stderr or '')
        ok = (p.returncode == 0) and ('OK' in out)
        if ok:
            return True, 'model test ok'
        return False, out[-500:]
    except subprocess.TimeoutExpired:
        return False, 'test timeout'
    except Exception as e:
        return False, f'exception: {e}'


def apply_primary(cfg, model_id: str):
    set_primary_model(cfg, model_id)
    save_openclaw_config(cfg)
    subprocess.run(['openclaw', 'gateway', 'restart'], capture_output=True, text=True)


def _should_probe():
    probe = R.get('CANDIDATE_PROBE') or {}
    return bool(probe.get('enabled', True))


def _probe_timeout():
    probe = R.get('CANDIDATE_PROBE') or {}
    return int(probe.get('timeoutSec', 30) or 30)


def _probe_candidate(cfg, candidate_model):
    old = R['TEST_TIMEOUT_SEC']
    R['TEST_TIMEOUT_SEC'] = _probe_timeout()
    try:
        return try_switch_and_test(cfg, candidate_model)
    finally:
        R['TEST_TIMEOUT_SEC'] = old


def try_switch_and_test(cfg, candidate_model):
    apply_primary(cfg, candidate_model)
    return test_current_default_model()


def pick_working_fallback(cfg, target_primary, state):
    all_models = list_configured_models(cfg)
    allowed = R.get('ALLOWED_FALLBACKS') or []
    candidates = []
    for m in all_models:
        if m == target_primary:
            continue
        if allowed and m not in allowed:
            continue
        provider = m.split('/', 1)[0]
        if provider in R['EXCLUDED_PROVIDERS']:
            continue
        if _is_in_cooldown(state, m):
            continue
        candidates.append(m)

    candidates = rank_candidates(candidates)

    if not candidates:
        return None, 'no fallback candidates'

    for c in candidates:
        if _should_probe():
            ok, detail = _probe_candidate(cfg, c)
        else:
            ok, detail = try_switch_and_test(cfg, c)
        log(f'fallback switch-test: {c} -> {"OK" if ok else "FAIL"}')
        if ok:
            return c, 'ok'
        err_type = _classify_error(detail)
        _mark_candidate_failure(state, c, err_type, detail)
    return None, 'all candidates failed'


def run_once():
    state = load_state()
    cfg = load_openclaw_config()
    current = get_primary_model(cfg)
    target_primary = get_target_primary(cfg)

    if not target_primary:
        log('ABORT: cannot determine primary model (set primaryModel in config.json)')
        return 2

    if current == target_primary:
        ok, detail = test_current_default_model()
        if ok:
            if state.get('consecutive_failures', 0) != 0:
                log('primary recovered; reset failure counter')
            state['consecutive_failures'] = 0
            state['consecutive_fallback_health'] = 0
            state['current_fallback'] = None
            save_state(state)
            return 0

        state['consecutive_failures'] = int(state.get('consecutive_failures', 0)) + 1
        save_state(state)
        log(f'primary failed ({state["consecutive_failures"]}/{R["FAIL_THRESHOLD"]}): {detail}')

        err_type = _classify_error(detail)
        if err_type not in R['FAILOVER_ON_ERRORS']:
            log(f'primary error not eligible for failover: {err_type}')
            return 0

        if state['consecutive_failures'] >= R['FAIL_THRESHOLD']:
            next_model, reason = pick_working_fallback(cfg, target_primary, state)
            if not next_model:
                log(f'FAILOVER ABORT: {reason}')
                save_state(state)
                apply_primary(cfg, target_primary)
                return 2
            state['last_switch'] = {
                'from': target_primary,
                'to': next_model,
                'at': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            state['current_fallback'] = next_model
            state['consecutive_failures'] = 0
            state['consecutive_fallback_health'] = 0
            save_state(state)
            log(f'FAILOVER DONE: {target_primary} -> {next_model}')
        return 0

    # running on fallback
    ok, detail = test_current_default_model()
    if ok:
        state['consecutive_fallback_health'] = int(state.get('consecutive_fallback_health', 0)) + 1
        log(f'fallback healthy ({state["consecutive_fallback_health"]}/{R["RECOVER_THRESHOLD"]}) on {current}')
        if state['consecutive_fallback_health'] >= R['RECOVER_THRESHOLD']:
            apply_primary(cfg, target_primary)
            ok2, detail2 = test_current_default_model()
            if ok2:
                state['last_switch'] = {
                    'from': current,
                    'to': target_primary,
                    'at': time.strftime('%Y-%m-%d %H:%M:%S')
                }
                state['current_fallback'] = None
                state['consecutive_fallback_health'] = 0
                state['consecutive_failures'] = 0
                save_state(state)
                log(f'FAILBACK DONE: {current} -> {target_primary}')
                return 0
            apply_primary(cfg, current)
            state['consecutive_fallback_health'] = 0
            save_state(state)
            log(f'FAILBACK ABORT: primary still unstable, reverted to {current}. detail={detail2}')
            return 0
    else:
        if state.get('consecutive_fallback_health', 0) != 0:
            log(f'fallback unhealthy; reset fallback health counter: {detail}')
        state['consecutive_fallback_health'] = 0

    state['consecutive_failures'] = 0
    save_state(state)
    return 0


def run_loop():
    log(
        f'failover loop started, interval={R["CHECK_INTERVAL_SEC"]}s, '
        f'fail_threshold={R["FAIL_THRESHOLD"]}, recover_threshold={R["RECOVER_THRESHOLD"]}'
    )
    while True:
        try:
            run_once()
        except Exception as e:
            log(f'run_once error: {e}')
        time.sleep(R['CHECK_INTERVAL_SEC'])


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'once'
    if mode == 'loop':
        run_loop()
    else:
        sys.exit(run_once())
