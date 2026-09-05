"""pygbag으로 웹(WASM) 빌드를 만들고 터치 오버레이를 주입한다.

사용법:
    pip install pygbag
    python mobile/build_web.py

결과물은 프로젝트 루트의 build/web/ 에 생성된다.
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD_WEB = ROOT / "build" / "web"
OVERLAY_FILE = Path(__file__).resolve().parent / "touch_overlay.html"


def run_pygbag_build():
    subprocess.run(
        [sys.executable, "-m", "pygbag", "--disable-sound-format-error", "--build", "main.py"],
        cwd=ROOT,
        check=True,
    )


def inject_overlay():
    index_path = BUILD_WEB / "index.html"
    if not index_path.exists():
        raise SystemExit(f"pygbag 빌드 결과를 찾을 수 없습니다: {index_path}")

    html = index_path.read_text(encoding="utf-8")
    overlay = OVERLAY_FILE.read_text(encoding="utf-8")

    if "touch-controls" in html:
        print("오버레이가 이미 주입되어 있습니다. 건너뜁니다.")
        return

    if "</body>" not in html:
        raise SystemExit("index.html에서 </body>를 찾을 수 없습니다.")

    html = html.replace("</body>", overlay + "\n</body>")
    index_path.write_text(html, encoding="utf-8")
    print(f"터치 오버레이를 주입했습니다: {index_path}")


def main():
    run_pygbag_build()
    inject_overlay()
    print(f"완료. 결과물: {BUILD_WEB}")
    print("로컬 확인: python -m http.server --directory build/web 8000")


if __name__ == "__main__":
    main()
