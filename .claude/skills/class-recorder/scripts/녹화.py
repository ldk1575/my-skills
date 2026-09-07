#!/usr/bin/env python3
"""수업 중에 손으로 녹화를 조종한다. 감시기가 돌고 있어도 안전하다.

    python 녹화.py            지금 상태
    python 녹화.py 정지        일시정지  ← 쉬는 시간엔 이것
    python 녹화.py 재개        다시 시작
    python 녹화.py 토글        정지 ↔ 재개 (한 손가락으로)
    python 녹화.py 시작        녹화 시작
    python 녹화.py 중지        녹화 끝내고 파일 저장
    python 녹화.py 대기        감시기 잠재우기 (자동 시작 안 함)
    python 녹화.py 해제        감시기 깨우기

왜 '중지'가 아니라 '정지'인가
    중지는 파일을 끊는다 — 한 수업이 조각조각 난다. 게다가 Zep이 떠 있으면
    감시기가 20초 안에 다시 켠다.
    일시정지는 같은 파일을 이어 쓰고, 감시기도 '녹화 중'으로 보므로 건드리지 않는다.
    쉬는 시간에는 '정지'를 쓴다.
"""

import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

HERE = Path(__file__).resolve().parent
CONFIG = HERE / "설정.json"
STANDBY = HERE / "대기중.flag"      # 있으면 감시기가 아무 일도 하지 않는다

별칭 = {
    "정지": "pause", "일시정지": "pause", "p": "pause",
    "재개": "resume", "r": "resume", "계속": "resume",
    "토글": "toggle", "t": "toggle",
    "시작": "start", "s": "start",
    "중지": "stop", "끝": "stop", "종료": "stop",
    "대기": "standby", "해제": "wake",
    "상태": "status", "": "status",
}


def 접속():
    if not CONFIG.exists():
        print("설정.json이 없습니다. 감시기.py를 한 번 실행하세요.")
        sys.exit(1)
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    try:
        import contextlib, io
        import obsws_python as obs
        with contextlib.redirect_stderr(io.StringIO()), \
             contextlib.redirect_stdout(io.StringIO()):
            return obs.ReqClient(host=cfg["obs_호스트"], port=cfg["obs_포트"],
                                 password=cfg["obs_비밀번호"], timeout=3)
    except Exception:
        print("OBS에 연결할 수 없습니다.")
        print("  · OBS가 켜져 있나요?")
        print("  · 도구 → WebSocket 서버 설정에서 서버가 켜져 있나요?")
        sys.exit(1)


def 상태(c):
    s = c.get_record_status()
    if not s.output_active:
        말 = "멈춤 (녹화 안 하는 중)"
    elif getattr(s, "output_paused", False):
        말 = f"일시정지 · {s.output_timecode[:8]}"
    else:
        말 = f"녹화 중 · {s.output_timecode[:8]}"
    mb = getattr(s, "output_bytes", 0) / 1048576
    print(f"{말}{f'  ({mb:.0f} MB)' if mb else ''}"
          + ("   [감시기 대기 중]" if STANDBY.exists() else ""))
    return s


def main():
    낱말 = sys.argv[1] if len(sys.argv) > 1 else ""
    if 낱말 in ("-h", "--help", "도움말"):
        print(__doc__)
        return 0

    명령 = 별칭.get(낱말)
    if 명령 is None:
        print(f"모르는 명령: {낱말}")
        print("쓸 수 있는 것: " + " · ".join(sorted(set(별칭) - {""})))
        return 2

    # 감시기 재우기·깨우기는 OBS와 무관하다
    if 명령 == "standby":
        STANDBY.write_text("", encoding="utf-8")
        print("감시기를 재웠습니다 — 자동으로 켜지지 않습니다.")
        print("다시 켜려면: python 녹화.py 해제")
        return 0
    if 명령 == "wake":
        STANDBY.unlink(missing_ok=True)
        print("감시기를 깨웠습니다 — Zep이 보이면 다시 자동으로 녹화합니다.")
        return 0

    c = 접속()
    s = c.get_record_status()
    쉼 = getattr(s, "output_paused", False)

    if 명령 == "status":
        상태(c)
        return 0

    if 명령 == "pause":
        if not s.output_active:
            print("녹화 중이 아닙니다. 시작하려면: python 녹화.py 시작")
            return 1
        if 쉼:
            print(f"이미 일시정지 상태입니다 · {s.output_timecode[:8]}")
            return 0
        c.pause_record()
        print(f"일시정지했습니다 · {s.output_timecode[:8]} 지점")
        print("재개: python 녹화.py 재개")
        return 0

    if 명령 == "resume":
        if not s.output_active:
            print("녹화 중이 아닙니다. 시작하려면: python 녹화.py 시작")
            return 1
        if not 쉼:
            print(f"이미 녹화 중입니다 · {s.output_timecode[:8]}")
            return 0
        c.resume_record()
        print(f"재개했습니다 · {s.output_timecode[:8]} 지점부터")
        return 0

    if 명령 == "toggle":
        if not s.output_active:
            print("녹화 중이 아닙니다. 시작하려면: python 녹화.py 시작")
            return 1
        c.toggle_record_pause()
        print(("재개했습니다" if 쉼 else "일시정지했습니다")
              + f" · {s.output_timecode[:8]} 지점")
        return 0

    if 명령 == "start":
        if s.output_active:
            print(f"이미 녹화 중입니다 · {s.output_timecode[:8]}")
            return 0
        c.start_record()
        print("녹화를 시작했습니다.")
        return 0

    if 명령 == "stop":
        if not s.output_active:
            print("녹화 중이 아닙니다.")
            return 0
        r = c.stop_record()
        print(f"녹화를 끝냈습니다 · {s.output_timecode[:8]}")
        print(f"  {getattr(r, 'output_path', '')}")
        if not STANDBY.exists():
            print("\n⚠ Zep이 떠 있으면 감시기가 20초 안에 다시 켭니다.")
            print("  아예 멈추려면: python 녹화.py 대기")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
