"""참고 영상의 정보·댓글·원문을 받아 폴더에 저장한다.

사용: python 도구/자막받기.py <유튜브 링크> <저장 폴더>
결과: 정보.json, 댓글.txt, 원문.txt
자막 요청이 막히면(429 등) 음성을 받아 faster-whisper로 받아쓴다.
"""
import json, subprocess, sys, glob, os, re

url, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
YT = [sys.executable, "-m", "yt_dlp"]


def run(args):
    return subprocess.run(YT + args, capture_output=True, text=True, encoding="utf-8", errors="replace")


# 1. 정보 + 댓글 상위 30개
r = run(["--skip-download", "--dump-json", "--write-comments",
         "--extractor-args", "youtube:max_comments=30,all,0,0;comment_sort=top", url])
try:
    info = json.loads(r.stdout.splitlines()[-1])
    keep = {k: info.get(k) for k in ("title", "channel", "channel_follower_count", "view_count",
                                     "like_count", "comment_count", "upload_date", "duration", "description")}
    json.dump(keep, open(f"{out}/정보.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(f"{out}/댓글.txt", "w", encoding="utf-8") as f:
        for c in info.get("comments") or []:
            f.write(f"[{c.get('like_count', 0)}] {c.get('text', '').strip()}\n")
except Exception as e:
    print("정보 받기 실패:", e, r.stderr[-300:])

# 2. 자막(한국어 → 영어)
r = run(["--skip-download", "--write-subs", "--write-auto-subs", "--sub-langs", "ko,ko-orig,en",
         "--sub-format", "vtt", "-o", f"{out}/_sub.%(ext)s", url])
vtts = sorted(glob.glob(f"{out}/_sub*.vtt"))
if vtts:
    lines, prev = [], None
    for ln in open(vtts[0], encoding="utf-8"):
        ln = re.sub(r"<[^>]+>", "", ln).strip()
        if not ln or "-->" in ln or ln.startswith(("WEBVTT", "Kind:", "Language:")) or ln == prev:
            continue
        lines.append(ln); prev = ln
    open(f"{out}/원문.txt", "w", encoding="utf-8").write("\n".join(lines))
    for v in vtts: os.remove(v)
    print("자막으로 원문 저장 (자동자막이면 오탈자 많음)")
    sys.exit(0)

# 3. 자막이 막히면 음성 받아쓰기
print("자막 실패 → 음성 받아쓰기")
run(["-f", "bestaudio", "-o", f"{out}/_audio.%(ext)s", url])
audio = glob.glob(f"{out}/_audio.*")[0]
raw = f"{out}/_audio.raw"
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", audio, "-ac", "1", "-ar", "16000", "-f", "s16le", raw], check=True)
import numpy as np
from faster_whisper import WhisperModel
pcm = np.frombuffer(open(raw, "rb").read(), np.int16).astype(np.float32) / 32768
model = WhisperModel("small", device="cpu", compute_type="int8")
segs, _ = model.transcribe(pcm, language="ko", beam_size=1, vad_filter=True)
with open(f"{out}/원문.txt", "w", encoding="utf-8") as f:
    for s in segs:
        m, sec = divmod(int(s.start), 60)
        f.write(f"[{m:02d}:{sec:02d}] {s.text.strip()}\n")
for p in (audio, raw): os.remove(p)
print("받아쓰기로 원문 저장")
