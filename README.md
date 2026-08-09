# 🎮 GeoDashGame (Geometry Dash in Python)

Python Pygame으로 제작된 지오메트리 대시(Geometry Dash) 스타일 횡스크롤 아케이드 게임입니다.  
웹 브라우저(WebAssembly) 및 로컬 데스크톱 환경에서 바로 플레이할 수 있습니다.

🌐 **웹 브라우저 플레이 (GitHub Pages)**: [https://smercurysn-byte.github.io/GeoDashGame/](https://smercurysn-byte.github.io/GeoDashGame/)

---

## ✨ 게임 특징

- **큐브 / 비행(Ship) 모드**: 포탈을 통과하면 비행 모드로 변경되며 점프/비행 메카닉이 전환됩니다.
- **다양한 장애물**: 가시(Spike), 이동 기둥(Pillar), 공중 블록(Block), 낭떠러지(Pit)
- **보스전 시스템**:
  - 드래곤 보스 (Dragon Boss)
  - 기사 보스 (Knight Boss)
  - 마왕 보스 (Demon Lord Boss)
  - 히든 미러 보스 (Hidden Mirror Boss)
- **패리 & 돌진 메카닉**: 보스전 시 방향키 이동, SPACE 돌진, BACKSPACE 패리(방어) 지원

---

## 🕹️ 조작법 (Controls)

### 일반 모드
- `SPACE`: 점프 (큐브 모드) / 상승 비행 (비행 모드) / 게임 재시작

### 보스전 모드
- `W`, `A`, `S`, `D` / 방향키: 플레이어 이동
- `SPACE`: 돌진 공격
- `BACKSPACE`: 패리 (적 공격 방어)
- `ESC`: 보스전 나가기

---

## 🔑 치트코드 (Cheat Codes)

게임 플레이 중 아래 키 조합을 순서대로 누르면 특수 모드가 열립니다.

1. **`030605`**: 전체 연속 보스전 진입
2. **`20140306`**: 보스 선택 모드 진입 (드래곤 / 기사 / 마왕 선택 입력)

---

## 🚀 로컬 실행 방법 (Local Setup)

### 요구 사항
- Python 3.8+
- Pygame 2.0+

```bash
# 1. 레포지토리 클론
git clone https://github.com/smercurysn-byte/GeoDashGame.git
cd GeoDashGame

# 2. 의존성 설치
pip install pygame

# 3. 게임 실행
python main.py
```

---

## 🌐 웹 빌드 (Pygbag Web Build)

```bash
pip install pygbag
python -m pygbag --disable-sound-format-error --build .
```
