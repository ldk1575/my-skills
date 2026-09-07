#!/usr/bin/env python3
"""수업이 시작되면 OBS 녹화를 켜고, 끝나면 끈다.

    python 감시기.py            상주 실행 (기본)
    python 감시기.py --status   지금 상태만 보고 끝낸다
    python 감시기.py --once     한 번만 판단한다 (스케줄러용)
    python 감시기.py --dry-run  판단만 하고 OBS는 건드리지 않는다

설정은 같은 폴더의 설정.json 을 읽는다. 없으면 만들어 준다.

원칙
  · 이미 녹화 중이면 손대지 않는다 (손수 시작한 녹화를 끊지 않는다)
  · 중지는 반드시 websocket으로 한다 (프로세스를 죽이면 파일이 깨진다)
  · OBS 자체를 끄지 않는다 — 녹화만 멈춘다
  · 감시 시간대 밖에서는 아무것도 하지 않는다
"""

import argparse
import ctypes
import json
import subprocess
import sys
import time
from ctypes import wintypes
from datetime import datetime, time as dtime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

HERE = Path(__file__).resolve().parent
CONFIG = HERE / "설정.json"
LOGDIR = HERE / "로그"
STANDBY = HERE / "대기중.flag"   # 녹화.py 대기/해제 가 만들고 지운다
WEEKDAYS = "월화수목금토일"

DEFAULTS = {
    "zep_키워드": ["ZEP", "zep.us"],
    "요일": [0, 1, 2, 3, 4],           # 0=월 … 6=일
    "시작시각": "09:30",
    "종료시각": "19:30",
    "여유_분": 25,        # Zep이 사라진 뒤 이만큼 지나야 중지
    "알림_분": 5,         # 이만큼 넘게 안 보일 때만 로그에 남긴다(탭 전환 무시)
    "폴링_초": 20,
    "obs_경로": r"C:\Program Files\obs-studio\bin\64bit\obs64.exe",
    "obs_호스트": "localhost",
    "obs_포트": 4455,
    "obs_비밀번호": "",                 # OBS → 도구 → WebSocket 서버 설정에서 복사
}


# ────────────────────────────── 설정 · 로그 ──────────────────────────────

def load_config() -> dict:
    if not CONFIG.exists():
        CONFIG.write_text(json.dumps(DEFAULTS, ensure_ascii=False, indent=2),
                          encoding="utf-8")
        print(f"설정 파일을 만들었습니다: {CONFIG}")
        print("OBS → 도구 → WebSocket 서버 설정에서 비밀번호를 복사해 "
              "'obs_비밀번호'에 넣어 주세요.")
        sys.exit(0)
    cfg = dict(DEFAULTS)
    cfg.update(json.loads(CONFIG.read_text(encoding="utf-8")))
    return cfg


def log(msg: str):
    LOGDIR.mkdir(exist_ok=True)
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(line, flush=True)
    with open(LOGDIR / f"{datetime.now():%Y-%m}.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ────────────────────────────── Zep 창 감지 ──────────────────────────────

def window_titles() -> list[str]:
    """보이는 최상위 창의 제목들. 외부 패키지 없이 ctypes만 쓴다."""
    titles = []
    u = ctypes.windll.user32
    proto = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def cb(hwnd, _):
        if not u.IsWindowVisible(hwnd):
            return True
        n = u.GetWindowTextLengthW(hwnd)
        if n:
            buf = ctypes.create_unicode_buffer(n + 1)
            u.GetWindowTextW(hwnd, buf, n + 1)
            titles.append(buf.value)
        return True

    u.EnumWindows(proto(cb), 0)
    return titles


def zep_보임(keywords) -> str | None:
    """Zep 창이 보이면 그 제목을 돌려준다."""
    for t in window_titles():
        low = t.lower()
        for k in keywords:
            if k.lower() in low:
                return t
    return None


# ──────────────────────────────── OBS ────────────────────────────────

class OBS:
    def __init__(self, cfg):
        self.cfg, self.cl = cfg, None

    def 실행중(self) -> bool:
        r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq obs64.exe"],
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        return "obs64.exe" in (r.stdout or "")

    def 띄우기(self):
        exe = Path(self.cfg["obs_경로"])
        if not exe.exists():
            log(f"OBS를 찾을 수 없음: {exe}")
            return False
        subprocess.Popen([str(exe), "--minimize-to-tray", "--disable-shutdown-check"],
                         cwd=str(exe.parent))
        log("OBS를 띄웠습니다 — 준비될 때까지 기다립니다")
        for _ in range(20):
            time.sleep(1.5)
            if self.연결():
                return True
        return False

    def 연결(self) -> bool:
        if self.cl:
            return True
        try:
            import obsws_python as obs
            # OBS가 꺼져 있거나 웹소켓이 아직이면 라이브러리가 예외 추적을
            # 통째로 찍는다. 20초마다 도는 감시기라 로그가 못 쓰게 되므로 삼킨다.
            import contextlib, io, os
            buf = io.StringIO()
            with contextlib.redirect_stderr(buf), contextlib.redirect_stdout(buf):
                self.cl = obs.ReqClient(host=self.cfg["obs_호스트"],
                                        port=self.cfg["obs_포트"],
                                        password=self.cfg["obs_비밀번호"],
                                        timeout=3)
            return True
        except Exception:
            self.cl = None
            return False

    def 녹화중(self):
        """True/False, 연결이 안 되면 None."""
        if not self.연결():
            return None
        try:
            return bool(self.cl.get_record_status().output_active)
        except Exception:
            self.cl = None
            return None

    def 시작(self) -> bool:
        if not self.연결():
            return False
        try:
            self.cl.start_record()
            return True
        except Exception as e:
            log(f"녹화 시작 실패: {e}")
            self.cl = None
            return False

    def 중지(self):
        """멈추고 저장된 파일 경로를 돌려준다."""
        if not self.연결():
            return None
        try:
            return getattr(self.cl.stop_record(), "output_path", "")
        except Exception as e:
            log(f"녹화 중지 실패: {e}")
            self.cl = None
            return None


# ──────────────────────────────── 판단 ────────────────────────────────

def 감시시간대(cfg, now: datetime) -> bool:
    if now.weekday() not in cfg["요일"]:
        return False
    s = dtime(*map(int, cfg["시작시각"].split(":")))
    e = dtime(*map(int, cfg["종료시각"].split(":")))
    return s <= now.time() <= e


def 상태보기(cfg, obs: OBS):
    now = datetime.now()
    z = zep_보임(cfg["zep_키워드"])
    rec = obs.녹화중()
    print(f"{'지금':12} {now:%Y-%m-%d(%a) %H:%M:%S}  ({WEEKDAYS[now.weekday()]}요일)")
    print(f"{'감시 시간대':12} {'예' if 감시시간대(cfg, now) else '아니오'}"
          f"  ({cfg['시작시각']}~{cfg['종료시각']}, "
          f"{''.join(WEEKDAYS[d] for d in cfg['요일'])})")
    print(f"{'Zep 창':12} {z if z else '안 보임'}")
    연결 = "됨" if rec is not None else "안 됨 (웹소켓 서버·비밀번호 확인)"
    녹화 = "녹화 중" if rec else "멈춤" if rec is False else "-"
    print(f"{'OBS 실행':12} {'예' if obs.실행중() else '아니오'}")
    print(f"{'OBS 연결':12} {연결}")
    print(f"{'녹화 상태':12} {녹화}")


def 한번판단(cfg, obs: OBS, state: dict, dry: bool):
    """state = {'사라진시각': datetime|None, '내가시작': bool}"""
    now = datetime.now()

    # 사람이 '쉬기'나 '대기'로 재워 뒀으면 아무것도 하지 않는다.
    # (손으로 중지한 걸 20초 뒤에 다시 켜 버리면 곤란하다)
    #
    # '쉬기'는 만료 시각을 적어 둔다 — 그 시각이 지나면 스스로 깨어난다.
    # 다음 교시에 '시작'을 깜빡해도 수업을 놓치지 않게 하려는 안전장치다.
    if STANDBY.exists():
        만료 = None
        try:
            글 = STANDBY.read_text(encoding="utf-8").strip()
            만료 = datetime.fromisoformat(글) if 글 else None
        except (OSError, ValueError):
            만료 = None

        if 만료 and now >= 만료:
            STANDBY.unlink(missing_ok=True)
            state["대기알림"] = False
            log("쉬는 시간이 끝났습니다 — 자동 판단을 다시 시작합니다")
        else:
            if not state.get("대기알림"):
                state["대기알림"] = True
                남 = f"{(만료 - now).total_seconds() / 60:.0f}분 뒤 자동 복귀" \
                    if 만료 else "해제할 때까지"
                log(f"쉬는 중입니다 — 자동 시작·중지를 하지 않습니다 ({남})")
            return
    elif state.get("대기알림"):
        state["대기알림"] = False
        log("대기 해제 — 자동 판단을 다시 시작합니다")

    안 = 감시시간대(cfg, now)
    z = zep_보임(cfg["zep_키워드"])

    if not 안:
        if state["내가시작"]:
            if dry:
                log("[가정] 감시 시간대가 끝나 중지하겠습니다")
            else:
                p = obs.중지()
                log(f"감시 시간대 종료 — 녹화 중지 {p or ''}")
            state["내가시작"] = False
        return

    rec = obs.녹화중()

    if z:
        state["사라진시각"] = None
        state["사라짐알림"] = False

        if rec is True:
            state["연결경고"] = False
            # 감시기를 도중에 재시작했는데 이미 녹화 중이고 Zep도 보인다면,
            # 그건 이 수업 녹화다. 이어받아야 끝날 때 자동으로 멈춘다.
            # (Zep이 안 보이는 녹화는 남의 것이므로 손대지 않는다)
            if not state["내가시작"] and not state.get("인수함"):
                state["인수함"] = True
                state["내가시작"] = True
                log(f"이미 녹화 중이고 Zep도 보입니다 — 이어받습니다 ({z[:40]})")
            return                          # 녹화 자체는 건드리지 않는다

        if rec is False:                    # 연결됨 · 멈춰 있음 → 시작
            state["연결경고"] = False
            if dry:
                log(f"[가정] Zep 발견 — 녹화를 시작하겠습니다 ({z[:40]})")
                state["내가시작"] = True
            elif obs.시작():
                state["내가시작"] = True
                log(f"Zep 발견 — 녹화 시작 ({z[:40]})")
            return

        # rec is None — 연결이 안 된다. 원인이 둘이라 갈라서 알린다.
        if not obs.실행중():
            if dry:
                log(f"[가정] Zep 발견 · OBS가 꺼져 있어 띄우겠습니다 ({z[:40]})")
                state["내가시작"] = True
            elif obs.띄우기() and obs.녹화중() is False and obs.시작():
                state["내가시작"] = True
                log(f"OBS 실행 후 녹화 시작 ({z[:40]})")
        elif not state.get("연결경고"):
            # OBS는 떠 있는데 웹소켓이 안 붙는다 — 20초마다 도배하지 않게 한 번만
            state["연결경고"] = True
            log(f"Zep을 찾았지만 OBS에 연결할 수 없습니다 ({z[:40]}) "
                f"— 도구 → WebSocket 서버 설정 · 포트 {cfg['obs_포트']} · 비밀번호 확인")
        return

    # Zep이 안 보인다
    if not state["내가시작"]:
        return                      # 내가 켠 게 아니면 건드리지 않는다

    if state["사라진시각"] is None:
        state["사라진시각"] = now
        state["끊김"] = state.get("끊김", 0) + 1
        return          # 탭을 잠깐 옮긴 것일 수 있다 — 아직 알리지 않는다

    안보인지 = (now - state["사라진시각"]).total_seconds() / 60

    # 짧은 깜빡임(탭 전환)은 기록하지 않는다. 실제로 오래 사라졌을 때만 남긴다.
    if 안보인지 >= cfg["알림_분"] and not state.get("사라짐알림"):
        state["사라짐알림"] = True
        log(f"Zep이 {cfg['알림_분']}분 넘게 안 보입니다 — "
            f"{cfg['여유_분']}분까지 기다립니다")

    if 안보인지 >= cfg["여유_분"]:
        if dry:
            log("[가정] 여유 시간이 지나 중지하겠습니다")
        else:
            p = obs.중지()
            log(f"Zep 없음 {cfg['여유_분']}분 경과 — 녹화 중지 {p or ''}")
        # 감지가 몇 번 끊겼는지 한 줄로 남긴다. 잦으면 Zep을 별도 창으로 둘 때다.
        끊김 = state.get("끊김", 0)
        if 끊김 > 1:
            log(f"참고 — 이번 녹화 중 Zep 감지가 {끊김}회 끊겼습니다 "
                f"(여유 {cfg['여유_분']}분이 막아 줬습니다). "
                f"잦으면 Zep을 별도 창으로 띄워 두세요")
        state["내가시작"] = False
        state["사라진시각"] = None
        state["사라짐알림"] = False
        state["끊김"] = 0


# ──────────────────────────────── main ────────────────────────────────

def main():
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--status", action="store_true")
    p.add_argument("--once", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("-h", "--help", action="store_true")
    a = p.parse_args()
    if a.help:
        print(__doc__)
        return 0

    cfg = load_config()
    obs = OBS(cfg)

    if a.status:
        상태보기(cfg, obs)
        return 0

    state = {"사라진시각": None, "내가시작": False, "연결경고": False}

    if a.once:
        한번판단(cfg, obs, state, a.dry_run)
        return 0

    log(f"감시 시작 — {''.join(WEEKDAYS[d] for d in cfg['요일'])} "
        f"{cfg['시작시각']}~{cfg['종료시각']} · {cfg['폴링_초']}초마다 확인"
        + (" · [판단만]" if a.dry_run else ""))
    try:
        while True:
            try:
                한번판단(cfg, obs, state, a.dry_run)
            except Exception as e:
                log(f"오류(계속 진행): {e}")
            time.sleep(cfg["폴링_초"])
    except KeyboardInterrupt:
        log("감시 종료 (사용자 중단) — 녹화 중이면 그대로 둡니다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
