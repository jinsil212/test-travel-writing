import io
import sys

MD = sys.argv[1] if len(sys.argv) > 1 else "원고/미국도시13곳/대본_v2.md"
START = "<!-- 본문 시작 -" + "->"
END = "<!-- 본문 끝 -" + "->"

t = io.open(MD, encoding="utf-8").read()
b = t.split(START)[1].split(END)[0]
lines = [l for l in b.splitlines() if l.strip() and not l.startswith("#")]
body = "\n".join(lines)
n = len(body)
print(MD)
print("본문 글자수(공백 포함):", n)
print("분당 350자 기준 %.1f분 / 400자 기준 %.1f분" % (n / 350, n / 400))
print("문단 수:", len(lines))
for w in ["저희", "[각색]", "여러분", "묶", "일정"]:
    print(" -", w, body.count(w))
