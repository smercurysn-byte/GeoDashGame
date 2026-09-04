# 🎮 GeoDashGame (Geometry Dash in Python)

Python Pygame으로 제작된 지오메트리 대시(Geometry Dash) 스타일 횡스크롤 아케이드 게임입니다.  
내 컴퓨터(로컬)에서 직접 실행하거나 웹 브라우저(GitHub Pages)에서 바로 플레이할 수 있습니다.

---

## 💻 내 컴퓨터에서 게임 실행하는 방법 (PC 실행 가이드)

### 1단계: 파이썬(Python) 확인 및 설치
- 컴퓨터에 **Python 3.8 이상**이 설치되어 있어야 합니다.
- 터미널(명령 프롬프트/PowerShell)에서 아래 명령어로 파이썬 버전을 확인하세요:
  ```bash
  python --version
  ```

### 2단계: 프로젝트 다운로드 (클론)
터미널을 열고 아래 명령어를 입력하여 게임 소스 코드를 다운로드합니다:
```bash
git clone https://github.com/smercurysn-byte/GeoDashGame.git
cd GeoDashGame
```
*(Git이 없다면 저장소 우상단의 `Code` ➔ `Download ZIP` 버튼을 눌러 압축을 해제해도 됩니다.)*

### 3단계: Pygame 라이브러리 설치
게임 실행에 필요한 `pygame` 패키지를 설치합니다:
```bash
pip install pygame
```

### 4단계: 게임 실행 🚀
아래 명령어를 입력하면 게임 창이 열리며 즉시 실행됩니다:
```bash
python main.py
```

---

## 🌐 웹 브라우저에서 바로 플레이하기 (무설치)

파이썬 설치 없이 웹 브라우저에서 클릭 한 번으로 바로 플레이할 수 있습니다:
👉 **[GeoDashGame 웹 플레이 사이트 바로가기](https://smercurysn-byte.github.io/GeoDashGame/)**

---

## 🕹️ 조작법 (Controls)

### 1. 일반 메인 모드
- `SPACE`: 점프 (큐브 모드) / 상승 비행 (비행 모드) / 게임 오버 시 재시작

### 2. 보스전 모드
- `W`, `A`, `S`, `D` 또는 `방향키`: 플레이어 이동
- `SPACE`: 돌진 공격
- `BACKSPACE`: 패리 (적 공격 방어)
- `ESC`: 보스전 나가기

---

## 🔑 비밀 치트코드 (Cheat Codes)

게임 플레이 중 키보드로 아래 숫자를 순서대로 누르면 숨겨진 보스전 모드가 열립니다!

1. **`030605`**: 전체 보스 연전 진입 (드래곤 ➔ 기사 ➔ 마왕 ➔ 히든 미러 보스)
2. **`20140306`**: 원하는 보스를 선택할 수 있는 보스 선택 모드 진입

---

## ✨ 게임 주요 기능

- **듀얼 모드 메카닉**: 포탈 통과 시 큐브(Cube) 모드 ↔ 비행(Ship) 모드 전환
- **다양한 지형 장애물**: 가시(Spike), 높낮이 기둥(Pillar), 공중 블록(Block), 낭떠러지(Pit)
- **화려한 보스전 패턴**: 보스별 특수 공격 패턴, 페이즈 변화 및 흡수 애니메이션
