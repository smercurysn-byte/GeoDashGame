import pygame
import sys
import random
import math
import asyncio

# 기본 설정
WIDTH, HEIGHT = 800, 400
FPS = 60
GROUND_Y = HEIGHT - 50

WHITE = (255, 255, 255)
BLACK = (20, 20, 20)
CYAN = (0, 220, 220)
RED = (220, 50, 50)

GRAVITY = 1
JUMP_POWER = -16
SCROLL_SPEED = 6

# 비행(포탈) 모드용 물리값
SHIP_GRAVITY = 0.5
SHIP_THRUST = -1.1
SHIP_MAX_SPEED = 6

YELLOW = (240, 200, 0)
PURPLE = (170, 80, 220)
ORANGE = (255, 140, 0)
GREEN = (50, 220, 50)

# 030605 순서로 누르면 전체 보스전 진입
BOSS_CODE = [pygame.K_0, pygame.K_3, pygame.K_0, pygame.K_6, pygame.K_0, pygame.K_5]
# 2014 순서로 누르면 보스 선택 모드 진입
BOSS_SELECT_CODE = [pygame.K_2, pygame.K_0, pygame.K_1, pygame.K_4]
_MAX_CODE_LEN = max(len(BOSS_CODE), len(BOSS_SELECT_CODE))
BOSS_SELECT_LIST = ["드래곤", "기사", "마왕", "거울속의 나", "샌즈", "파피루스", "언다인", "토리엘", "아스리엘"]

pygame.init()
pygame.mixer.init()
pygame.mixer.music.load("assets/geodash_music.mp3")
pygame.mixer.music.play(-1)  # -1 = 무한 반복

# 실제 창은 모니터 화면 크기에 맞추고, 게임은 내부적으로 800x400 캔버스에 그린 뒤
# 화면 크기에 맞게 확대해서 보여준다 (좌표 기반 게임 로직은 그대로 유지).
# 배타적 전체화면(pygame.FULLSCREEN)은 알트탭 등으로 포커스를 잃으면 디스플레이 서피스가
# 깨지면서 다음 draw 호출에서 게임이 죽는 경우가 있어(대결 중 갑자기 꺼지는 원인),
# 테두리 없는 창 모드(NOFRAME)로 모니터 크기를 채우도록 한다.
_desktop_w, _desktop_h = pygame.display.get_desktop_sizes()[0]
window = pygame.display.set_mode((_desktop_w, _desktop_h), pygame.NOFRAME)
screen = pygame.Surface((WIDTH, HEIGHT))
pygame.display.set_caption("Geo Dash (Python)")
clock = pygame.time.Clock()


def present():
    """내부 게임 화면(screen)을 실제 창(window) 크기에 맞게 확대해 출력한다."""
    global window
    try:
        win_w, win_h = window.get_size()
        scale = min(win_w / WIDTH, win_h / HEIGHT)
        new_w, new_h = max(1, int(WIDTH * scale)), max(1, int(HEIGHT * scale))
        scaled = pygame.transform.scale(screen, (new_w, new_h))
        window.fill((0, 0, 0))
        window.blit(scaled, ((win_w - new_w) // 2, (win_h - new_h) // 2))
        pygame.display.flip()
    except pygame.error:
        # 포커스 변경 등으로 디스플레이 서피스가 일시적으로 깨졌을 때
        # 게임이 그대로 죽지 않도록 창을 다시 만들어 복구를 시도한다.
        try:
            dw, dh = pygame.display.get_desktop_sizes()[0]
            window = pygame.display.set_mode((dw, dh), pygame.NOFRAME)
        except pygame.error:
            pass


_ctrl_press_count = 0


def poll_events():
    """이벤트 큐를 읽으면서, Ctrl 키를 5번 연속으로 누르면 게임을 즉시 종료한다."""
    global _ctrl_press_count
    events = pygame.event.get()
    for ev in events:
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_LCTRL, pygame.K_RCTRL):
                _ctrl_press_count += 1
                if _ctrl_press_count >= 5:
                    pygame.quit()
                    sys.exit()
            else:
                _ctrl_press_count = 0
    return events


font = pygame.font.SysFont(None, 48)
try:
    korean_font = pygame.font.Font("C:/Windows/Fonts/malgun.ttf", 34)
except Exception:
    korean_font = pygame.font.SysFont("malgungothic", 34)

# 화면(400px) 안에 여러 줄을 담아야 하는 조작 안내/보스 선택 목록용 축소 폰트.
try:
    korean_font_sm = pygame.font.Font("C:/Windows/Fonts/malgun.ttf", 22)
except Exception:
    korean_font_sm = pygame.font.SysFont("malgungothic", 22)

DRAGON_IMAGE = pygame.image.load("assets/dragon.png").convert_alpha()
KNIGHT_IMAGE = pygame.image.load("assets/knight.png").convert_alpha()
DEMON_LORD_IMAGE = pygame.image.load("assets/demonlord.png").convert_alpha()
SANS_IMAGE = pygame.image.load("assets/sans.png").convert_alpha()
SANS_DEAD_IMAGE = pygame.image.load("assets/sans_dead.png").convert_alpha()
PAPYRUS_IMAGE = pygame.image.load("assets/papyrus.png").convert_alpha()
PAPYRUS_DEAD_IMAGE = pygame.image.load("assets/papyrus_dead.png").convert_alpha()
UNDYNE_IMAGE      = pygame.image.load("assets/undyne.png").convert_alpha()
UNDYNE_DEAD_IMAGE = pygame.image.load("assets/undyne_dead.png").convert_alpha()
TORIEL_IMAGE      = pygame.image.load("assets/toriel.png").convert_alpha()
TORIEL_DEAD_IMAGE = pygame.image.load("assets/toriel_dead.png").convert_alpha()
ASRIEL_IMAGE          = pygame.image.load("assets/asriel.png").convert_alpha()
ASRIEL_RETURNED_IMAGE = pygame.image.load("assets/asriel_returned.png").convert_alpha()

SWORD_SOUNDS = [
    pygame.mixer.Sound("assets/sword_clash.mp3"),
    pygame.mixer.Sound("assets/armor_impact.mp3"),
]

DRAGON_SOUNDS = [
    pygame.mixer.Sound("assets/dragon_breath1.mp3"),
    pygame.mixer.Sound("assets/dragon_breath2.mp3"),
    pygame.mixer.Sound("assets/dragon_sigh.mp3"),
    pygame.mixer.Sound("assets/dragon_roar.mp3"),
]


class Player:
    def __init__(self):
        self.size = 30
        self.x = 100
        self.y = GROUND_Y - self.size
        self.vel_y = 0
        self.on_ground = True
        self.mode = "cube"  # "cube" 또는 "ship"(포탈을 통과하면 비행 모드)
        self.angle = 0

    def jump(self):
        if self.mode == "cube" and self.on_ground:
            self.vel_y = JUMP_POWER
            self.on_ground = False

    def apply_gravity(self):
        self.prev_bottom = self.y + self.size
        self.vel_y += GRAVITY
        self.y += self.vel_y
        if not self.on_ground:
            self.angle -= 8  # 공중에서 시계방향 회전

    def land_on(self, top_y):
        self.y = top_y - self.size
        self.vel_y = 0
        self.on_ground = True
        self.angle = round(self.angle / 90) * 90  # 착지 시 90도 단위로 스냅

    def fly(self, thrust_held):
        thrust = SHIP_THRUST if thrust_held else 0
        self.vel_y += SHIP_GRAVITY + thrust
        self.vel_y = max(-SHIP_MAX_SPEED, min(SHIP_MAX_SPEED, self.vel_y))
        self.y += self.vel_y

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.size, self.size)

    def draw(self):
        color = YELLOW if self.mode == "ship" else CYAN
        if self.mode == "cube":
            surf = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
            pygame.draw.rect(surf, color, (0, 0, self.size, self.size))
            # 큐브 면에 선을 그려 회전이 잘 보이게
            pygame.draw.line(surf, BLACK, (self.size // 2, 0), (self.size // 2, self.size), 2)
            pygame.draw.line(surf, BLACK, (0, self.size // 2), (self.size, self.size // 2), 2)
            rotated = pygame.transform.rotate(surf, self.angle)
            rect = rotated.get_rect(center=(self.x + self.size // 2, self.y + self.size // 2))
            screen.blit(rotated, rect)
        else:
            pygame.draw.rect(screen, color, self.get_rect())


class Spike:
    """뾰족한 삼각형 장애물. 닿으면 죽음."""

    def __init__(self, x):
        self.size = 30
        self.x = x
        self.y = GROUND_Y - self.size

    def update(self):
        self.x -= SCROLL_SPEED

    def get_rect(self):
        # 삼각형이지만 충돌은 살짝 작은 사각형으로 간단하게 처리
        margin = 6
        return pygame.Rect(self.x + margin, self.y + margin, self.size - margin * 2, self.size - margin)

    def draw(self):
        points = [
            (self.x, self.y + self.size),
            (self.x + self.size // 2, self.y),
            (self.x + self.size, self.y + self.size),
        ]
        pygame.draw.polygon(screen, RED, points)

    @property
    def right(self):
        return self.x + self.size


class Pillar:
    """뛰어 넘어야 하는 키 큰 사각형 기둥. 위에는 올라설 수 있고, 옆면/아랫면에 부딪히면 죽음.

    bottom_cut을 주면 기둥 아랫부분을 잘라내어 공중에 뜬 블록으로 만든다.
    (꼭대기 위치는 그대로 유지되고, 바닥과의 사이에 빈 틈이 생겨 그 밑으로 지나갈 수 있다.)
    """

    def __init__(self, x, height, bottom_cut=0):
        self.width = 30
        self.height = height - bottom_cut
        self.x = x
        self.y = GROUND_Y - height

    def update(self):
        self.x -= SCROLL_SPEED

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def draw(self):
        pygame.draw.rect(screen, RED, self.get_rect())

    @property
    def right(self):
        return self.x + self.width


class Block:
    """비행(포탈) 구간에서 위/아래를 막아 통로를 만드는 장애물. 닿으면 죽음."""

    def __init__(self, x, y, height):
        self.width = 34
        self.x = x
        self.y = y
        self.height = height

    def update(self):
        self.x -= SCROLL_SPEED

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def draw(self):
        pygame.draw.rect(screen, PURPLE, self.get_rect())

    @property
    def right(self):
        return self.x + self.width


class Pit:
    """바닥이 끊긴 낭떠러지 구간. 점프로 넘지 못하면 떨어져 죽음."""

    def __init__(self, x, width):
        self.x = x
        self.width = width

    def update(self):
        self.x -= SCROLL_SPEED

    def contains_x(self, x):
        return self.x <= x < self.right

    def draw(self):
        rect = pygame.Rect(self.x, GROUND_Y, self.width, HEIGHT - GROUND_Y)
        pygame.draw.rect(screen, BLACK, rect)
        pygame.draw.line(screen, RED, (self.x, GROUND_Y), (self.x, HEIGHT), 2)
        pygame.draw.line(screen, RED, (self.right, GROUND_Y), (self.right, HEIGHT), 2)

    @property
    def right(self):
        return self.x + self.width


class Portal:
    """통과하면 모드를 바꿔주는 포탈. 닿아도 죽지 않음."""

    def __init__(self, x, to_mode):
        self.width = 14
        self.x = x
        self.to_mode = to_mode  # "ship" 또는 "cube"
        self.triggered = False

    def update(self):
        self.x -= SCROLL_SPEED

    def get_rect(self):
        return pygame.Rect(self.x, 0, self.width, GROUND_Y)

    def draw(self):
        color = YELLOW if self.to_mode == "ship" else CYAN
        pygame.draw.rect(screen, color, self.get_rect())

    @property
    def right(self):
        return self.x + self.width


class Particle:
    """플레이어가 움직일 때 뒤로 흩날리는 작은 입자."""

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = -SCROLL_SPEED * 0.5 + random.uniform(-1, 1)
        self.vy = random.uniform(-1.5, 1.5)
        self.life = 18
        self.max_life = self.life
        self.size = random.randint(2, 4)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1

    def alive(self):
        return self.life > 0

    def draw(self):
        ratio = max(self.life / self.max_life, 0)
        size = max(1, int(self.size * ratio))
        pygame.draw.circle(screen, CYAN, (int(self.x), int(self.y)), size)


# 한 번의 점프로 넘을 수 있는 대략적인 높이 (JUMP_POWER, GRAVITY 기준 최고 상승 높이)
MAX_JUMP_HEIGHT = (JUMP_POWER ** 2) // (2 * GRAVITY)


# 한 번의 점프로 넘을 수 있는 대략적인 가로 거리 (위로 올라갔다 내려오는 시간 x 이동 속도)
MAX_JUMP_DISTANCE = int(-2 * JUMP_POWER / GRAVITY) * SCROLL_SPEED


def make_cube_pattern(start_x):
    """땅 위를 달리는 구간(cube 모드)의 장애물 패턴."""
    pattern_type = random.choices(
        ["single_spike", "spike_row", "pillar", "pit"],
        weights=[30, 20, 20, 15],
    )[0]

    if pattern_type == "single_spike":
        obstacles = [Spike(start_x)]
        next_x = start_x + random.randint(280, 420)

    elif pattern_type == "spike_row":
        count = random.randint(2, 3)
        obstacles = [Spike(start_x + i * 32) for i in range(count)]
        next_x = obstacles[-1].right + random.randint(280, 420)

    elif pattern_type == "pillar":
        height = random.randint(50, int(MAX_JUMP_HEIGHT * 0.8))
        obstacles = [Pillar(start_x, height)]
        next_x = start_x + random.randint(300, 450)

    else:  # pit (낭떠러지)
        width = random.randint(80, min(150, MAX_JUMP_DISTANCE - 20))
        obstacles = [Pit(start_x, width)]
        next_x = obstacles[0].right + random.randint(280, 420)

    return obstacles, next_x


def make_ship_pattern(start_x):
    """날아서 통과하는 구간(ship 모드)의 장애물 패턴. 위/아래 블록 사이 통로를 지나가야 함."""
    gap_height = random.randint(110, 150)
    gap_y = random.randint(30, GROUND_Y - 30 - gap_height)

    top = Block(start_x, 0, gap_y)
    bottom = Block(start_x, gap_y + gap_height, GROUND_Y - (gap_y + gap_height))

    obstacles = [top, bottom]
    next_x = start_x + random.randint(220, 300)
    return obstacles, next_x


def make_pattern(start_x, zone):
    if zone == "ship":
        return make_ship_pattern(start_x)
    return make_cube_pattern(start_x)


def reset_game():
    player = Player()
    obstacles = []
    spawn_x = WIDTH + 200
    zone = "cube"
    for _ in range(5):
        new_obs, spawn_x = make_pattern(spawn_x, zone)
        obstacles.extend(new_obs)
    next_portal_x = spawn_x + random.randint(500, 800)
    return player, obstacles, spawn_x, zone, next_portal_x, 0


# ===================== 보스전 (치트코드 030605) =====================

class BossPlayer:
    """보스전 전용 플레이어. 자유롭게 4방향 이동 + 돌진(대시) 공격."""

    def __init__(self):
        self.size = 26
        self.x = 120
        self.y = HEIGHT // 2
        self.speed = 4
        self.hp = 10
        self.max_hp = 10
        self.facing = (1, 0)
        self.dashing = False
        self.dash_timer = 0
        self.dash_dir = (1, 0)
        self.hit_cooldown = 0
        self.bound_timer = 0       # 사슬 속박 상태
        self.knockback_vx = 0.0    # 장벽 반사 넉백
        self.knockback_vy = 0.0
        self.wall_hit_shake = False  # 벽 충돌 진동 신호
        self.parry_enabled = False  # 거울 보스전에서만 True
        self.parry_timer = 0        # >0 이면 다음 피격 방어
        self.parry_cooldown = 0     # 연속 패리 방지
        self.heal_cooldown = 0      # E키 회복 쿨다운
        self.HEAL_MAX_CD = 420      # 7초 (60fps)

    def handle_move(self, keys):
        if self.dashing or self.bound_timer > 0:
            return
        dx = dy = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += 1
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy -= 1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy += 1
        if dx or dy:
            length = math.hypot(dx, dy)
            dx, dy = dx / length, dy / length
            self.facing = (dx, dy)
            self.x += dx * self.speed
            self.y += dy * self.speed
        self.x = max(self.size, min(WIDTH - self.size, self.x))
        self.y = max(self.size, min(HEIGHT - self.size, self.y))

    def try_dash(self):
        if not self.dashing and self.bound_timer <= 0:
            self.dashing = True
            self.dash_timer = 8
            self.dash_dir = self.facing

    def try_parry(self):
        if self.parry_enabled and self.parry_cooldown <= 0:
            self.parry_timer = 60       # 1초 패리 판정 창
            self.parry_cooldown = 50    # 재사용 대기

    def try_heal(self):
        if self.heal_cooldown <= 0 and self.hp < self.max_hp:
            self.hp = min(self.max_hp, self.hp + 3)
            self.heal_cooldown = self.HEAL_MAX_CD
            return True
        return False

    def update(self):
        if self.dashing:
            dx, dy = self.dash_dir
            self.x += dx * 14
            self.y += dy * 14
            self.x = max(self.size, min(WIDTH - self.size, self.x))
            self.y = max(self.size, min(HEIGHT - self.size, self.y))
            self.dash_timer -= 1
            if self.dash_timer <= 0:
                self.dashing = False
        if self.hit_cooldown > 0:
            self.hit_cooldown -= 1
        if self.heal_cooldown > 0:
            self.heal_cooldown -= 1
        if self.bound_timer > 0:
            self.bound_timer -= 1
        if self.parry_timer > 0:
            self.parry_timer -= 1
        if self.parry_cooldown > 0:
            self.parry_cooldown -= 1
        self.wall_hit_shake = False
        if abs(self.knockback_vx) > 0.2 or abs(self.knockback_vy) > 0.2:
            new_x = self.x + self.knockback_vx
            new_y = self.y + self.knockback_vy
            cl_x = max(self.size, min(WIDTH - self.size, new_x))
            cl_y = max(self.size, min(HEIGHT - self.size, new_y))
            if (cl_x != new_x or cl_y != new_y) and (abs(self.knockback_vx) > 4 or abs(self.knockback_vy) > 4):
                self.wall_hit_shake = True
            self.x = cl_x
            self.y = cl_y
            self.knockback_vx *= 0.75
            self.knockback_vy *= 0.75
        else:
            self.knockback_vx = 0.0
            self.knockback_vy = 0.0

    def take_damage(self, amount, melee=False):
        if self.dashing or self.hit_cooldown > 0:
            return False
        # 패리 성공: 근접 공격(melee=True)에만 유효
        if self.parry_timer > 0 and melee:
            self.parry_timer = 0
            self.parry_cooldown = 50
            self.hit_cooldown = 20
            return "parried"
        self.hp -= amount
        self.hit_cooldown = 12
        return True

    def get_rect(self):
        return pygame.Rect(self.x - self.size // 2, self.y - self.size // 2, self.size, self.size)

    def draw(self):
        if self.dashing:
            color = YELLOW
        elif self.parry_timer > 0:
            color = (200, 0, 255) if self.parry_timer % 6 < 3 else (120, 0, 180)
        elif self.bound_timer > 0:
            color = (150, 0, 200)
        elif self.hit_cooldown > 0 and self.hit_cooldown % 10 < 5:
            color = WHITE
        else:
            color = CYAN
        pygame.draw.rect(screen, color, self.get_rect())
        if self.bound_timer > 0:
            cx, cy = int(self.x), int(self.y + self.size // 2 + 8)
            pygame.draw.circle(screen, PURPLE, (cx, cy), 10, 2)


def wander(boss, min_x, max_x, min_y=40, max_y=HEIGHT - 40, speed=1.0):
    """보스가 느린 속도로 랜덤한 방향을 향해 이리저리 떠다니게 만든다."""
    boss.wander_timer -= 1
    if boss.wander_timer <= 0:
        angle = random.uniform(0, 2 * math.pi)
        boss.wander_dir = (math.cos(angle), math.sin(angle))
        boss.wander_timer = random.randint(60, 120)
    boss.x += boss.wander_dir[0] * speed
    boss.y += boss.wander_dir[1] * speed
    boss.x = max(min_x, min(max_x, boss.x))
    boss.y = max(min_y, min(max_y, boss.y))


def teleport_near(boss, player, gap=5):
    """근접 공격을 시작할 때 플레이어와 5픽셀 거리로 순간이동."""
    dx = boss.x - player.x
    dy = boss.y - player.y
    dist = math.hypot(dx, dy) or 1
    dx, dy = dx / dist, dy / dist
    total = player.size / 2 + boss.size / 2 + gap
    boss.x = player.x + dx * total
    boss.y = player.y + dy * total
    boss.x = max(boss.size // 2, min(WIDTH - boss.size // 2, boss.x))
    boss.y = max(boss.size // 2, min(HEIGHT - boss.size // 2, boss.y))


CARDINAL_DIRS = [(0, -1), (0, 1), (-1, 0), (1, 0)]  # 상, 하, 좌, 우


def in_cardinal_wedge(boss, player, length, half_angle_deg=45):
    """플레이어가 보스 기준 상하좌우 90도 부채꼴(반원 아님) 범위 안에 있는지 검사."""
    dx, dy = player.x - boss.x, player.y - boss.y
    dist = math.hypot(dx, dy)
    if dist == 0 or dist > length:
        return False
    ux, uy = dx / dist, dy / dist
    for ax, ay in CARDINAL_DIRS:
        cos_angle = ux * ax + uy * ay
        if cos_angle >= math.cos(math.radians(half_angle_deg)):
            return True
    return False


def wedge_points(cx, cy, direction, length, half_angle_deg=45, steps=10):
    """부채꼴(쐐기) 모양을 그리기 위한 다각형 좌표 리스트."""
    base_angle = math.atan2(direction[1], direction[0])
    half = math.radians(half_angle_deg)
    points = [(cx, cy)]
    for i in range(steps + 1):
        a = base_angle - half + (2 * half) * (i / steps)
        points.append((cx + math.cos(a) * length, cy + math.sin(a) * length))
    return points


class DragonBoss:
    """첫 번째 보스: 화염의 용. 패턴 종료 후 잠깐 무방비(vulnerable) 상태가 되며,
    그때 플레이어가 돌진 공격으로 부딪혀야 데미지가 들어간다."""

    name = "DRAGON"

    def __init__(self):
        self.x = WIDTH - 130
        self.y = HEIGHT // 2
        self.size = 90
        self.hp = 200
        self.max_hp = 200
        self.state = "idle"
        self.timer = 50
        self.pattern = None
        self.data = {}
        self.wander_dir = (0, 0)
        self.wander_timer = 0

    def get_rect(self):
        return pygame.Rect(self.x - self.size // 2, self.y - self.size // 2, self.size, self.size)

    def is_vulnerable(self):
        return self.state == "vulnerable" or (self.pattern == "cross_gust" and self.state == "active")

    def start_pattern(self):
        self.pattern = random.choice([
            "fire_breath", "tail_swipe", "fireball_rain", "fan_fire",
            "cross_gust", "triple_fireball", "fire_wall", "lava_zone",
            "flame_counter", "falling_rocks", "breath_sweep",
            "tail_wide", "fire_ring", "spine_fan",
        ])
        self.state = "telegraph"
        self.data = {}
        if self.pattern == "fire_breath":
            self.data["band_y"] = random.randint(60, HEIGHT - 60)
            self.timer = 50
        elif self.pattern == "tail_swipe":
            self.timer = 40
        elif self.pattern == "fan_fire":
            self.data["aim_angle"] = 0.0
            self.timer = 50
        elif self.pattern == "fireball_rain":
            self.data["points"] = [[random.randint(40, WIDTH - 200), random.randint(40, HEIGHT - 40), 70] for _ in range(5)]
            self.timer = 70
        elif self.pattern == "cross_gust":
            d = random.choice([-1, 1])
            self.data["dir"] = d
            self.x = float(WIDTH - 60) if d < 0 else 60.0
            self.y = random.uniform(HEIGHT * 0.25, HEIGHT * 0.75)
            self.timer = 40
        elif self.pattern == "triple_fireball":
            self.data.update({"shots_left": 3, "shot_delay": 0, "projs": [], "tgt": (0.0, 0.0)})
            self.timer = 40
        elif self.pattern == "fire_wall":
            self.data.update({"wall_x": float(WIDTH + 20), "gap_y": random.randint(90, HEIGHT - 90), "gap_h": 95})
            self.timer = 50
        elif self.pattern == "lava_zone":
            self.data["zones"] = [
                {"x": random.randint(60, WIDTH - 170), "y": random.randint(60, HEIGHT - 110),
                 "w": 110, "h": 65, "fuse": random.randint(35, 65), "erupt": 0}
                for _ in range(3)
            ]
            self.timer = 140
        elif self.pattern == "flame_counter":
            self.data.update({"trail": [], "charging": False, "charge_dir": (0.0, 0.0)})
            self.timer = 45
        elif self.pattern == "falling_rocks":
            step = max(55, (WIDTH - 200) // 4)
            xs = [100 + i * step for i in range(4)]
            random.shuffle(xs)
            self.data["rocks"] = [{"x": float(x), "y": -25.0, "delay": i * 28, "alive": True} for i, x in enumerate(xs)]
            self.timer = 55
        elif self.pattern == "breath_sweep":
            self.data.update({"angle": -math.pi / 2.0, "sweep_speed": math.pi / 90.0})
            self.timer = 55
        elif self.pattern == "tail_wide":
            self.timer = 40
        elif self.pattern == "fire_ring":
            self.data.update({"ring_x": 0.0, "ring_y": 0.0, "radius": 210.0, "inited": False})
            self.timer = 45
        elif self.pattern == "spine_fan":
            self.data.update({"aim_angle": 0.0, "projs": []})
            self.timer = 45

    def update(self, player):
        busy = (
            (self.pattern == "fan_fire" and self.state in ("telegraph", "active")) or
            (self.pattern == "cross_gust" and self.state == "active") or
            (self.pattern == "flame_counter" and self.state == "active") or
            (self.pattern == "breath_sweep" and self.state in ("telegraph", "active")) or
            (self.pattern in ("tail_swipe", "tail_wide") and self.state in ("windup", "active"))
        )
        if not busy:
            wander(self, WIDTH * 0.55, WIDTH - 70)

        if self.state == "idle":
            self.timer -= 1
            if self.timer <= 0:
                self.start_pattern()

        elif self.state == "telegraph":
            self.timer -= 1
            if self.pattern == "fireball_rain":
                for p in self.data["points"]:
                    p[2] -= 1
            if self.pattern in ("fan_fire", "spine_fan"):
                self.data["aim_angle"] = math.atan2(player.y - self.y, player.x - self.x)
            if self.pattern == "triple_fireball":
                self.data["tgt"] = (player.x, player.y)
            if self.pattern == "fire_ring":
                self.data["ring_x"] = float(player.x)
                self.data["ring_y"] = float(player.y)
            if self.timer <= 0:
                if self.pattern in ("tail_swipe", "tail_wide"):
                    teleport_near(self, player)
                    self.state = "windup"
                    self.timer = 55 if self.pattern == "tail_wide" else 60
                elif self.pattern == "fan_fire":
                    base = self.data["aim_angle"]
                    self.data["projs"] = [
                        {"x": float(self.x), "y": float(self.y),
                         "vx": math.cos(base - math.radians(60) + i * math.radians(20)) * 6.5,
                         "vy": math.sin(base - math.radians(60) + i * math.radians(20)) * 6.5,
                         "alive": True}
                        for i in range(7)
                    ]
                    self.state = "active"; self.timer = 130
                elif self.pattern == "spine_fan":
                    base = self.data["aim_angle"]
                    self.data["projs"] = [
                        {"x": float(self.x), "y": float(self.y),
                         "vx": math.cos(base - math.radians(15) + i * math.radians(15)) * 9.0,
                         "vy": math.sin(base - math.radians(15) + i * math.radians(15)) * 9.0,
                         "alive": True}
                        for i in range(3)
                    ]
                    self.state = "active"; self.timer = 100
                elif self.pattern == "cross_gust":
                    self.state = "active"; self.timer = 90
                elif self.pattern == "triple_fireball":
                    self.state = "active"; self.timer = 130
                elif self.pattern == "fire_wall":
                    self.state = "active"; self.timer = 240
                elif self.pattern == "lava_zone":
                    self.state = "active"; self.timer = 160
                elif self.pattern == "flame_counter":
                    self.state = "active"; self.timer = 110
                elif self.pattern == "falling_rocks":
                    self.state = "active"; self.timer = 210
                elif self.pattern == "breath_sweep":
                    self.state = "active"; self.timer = 100
                elif self.pattern == "fire_ring":
                    self.state = "active"; self.timer = 90
                else:
                    self.state = "active"
                    self.timer = {"fire_breath": 30, "fireball_rain": 20}[self.pattern]

        elif self.state == "windup":
            self.timer -= 1
            if self.timer <= 0:
                self.state = "active"
                self.timer = 25 if self.pattern == "tail_wide" else 20

        elif self.state == "active":
            self.timer -= 1
            if self.pattern == "fire_breath":
                if abs(player.y - self.data["band_y"]) < 35:
                    if player.take_damage(1): random.choice(DRAGON_SOUNDS).play()
            elif self.pattern == "tail_swipe":
                if math.hypot(player.x - self.x, player.y - self.y) < 140:
                    if player.take_damage(1): random.choice(DRAGON_SOUNDS).play()
            elif self.pattern == "fan_fire":
                all_dead = True
                for proj in self.data["projs"]:
                    if not proj["alive"]: continue
                    all_dead = False
                    proj["x"] += proj["vx"]; proj["y"] += proj["vy"]
                    if proj["x"] < -12 or proj["x"] > WIDTH + 12 or proj["y"] < -12 or proj["y"] > HEIGHT + 12:
                        proj["alive"] = False; continue
                    if math.hypot(player.x - proj["x"], player.y - proj["y"]) < 24:
                        if player.take_damage(1): random.choice(DRAGON_SOUNDS).play()
                        proj["alive"] = False
                if all_dead: self.timer = 0
            elif self.pattern == "fireball_rain":
                for p in self.data["points"]:
                    if p[2] <= 0 and math.hypot(player.x - p[0], player.y - p[1]) < 45:
                        if player.take_damage(1): random.choice(DRAGON_SOUNDS).play()

            # === NEW DRAGON PATTERNS ===
            elif self.pattern == "cross_gust":
                d = self.data["dir"]
                self.x += d * 24
                if not player.dashing and self.get_rect().colliderect(player.get_rect()):
                    player.take_damage(2)
                if (d < 0 and self.x < -self.size) or (d > 0 and self.x > WIDTH + self.size):
                    self.timer = 0

            elif self.pattern == "triple_fireball":
                self.data["shot_delay"] -= 1
                if self.data["shot_delay"] <= 0 and self.data["shots_left"] > 0:
                    dx = player.x - self.x; dy = player.y - self.y
                    dist = math.hypot(dx, dy) or 1
                    self.data["projs"].append({"x": float(self.x), "y": float(self.y),
                                               "vx": dx / dist * 7.0, "vy": dy / dist * 7.0, "alive": True})
                    self.data["shots_left"] -= 1
                    self.data["shot_delay"] = 26
                all_dead = self.data["shots_left"] == 0 and all(not p["alive"] for p in self.data["projs"])
                for proj in self.data["projs"]:
                    if not proj["alive"]: continue
                    proj["x"] += proj["vx"]; proj["y"] += proj["vy"]
                    if proj["x"] < -10 or proj["x"] > WIDTH + 10 or proj["y"] < -10 or proj["y"] > HEIGHT + 10:
                        proj["alive"] = False; continue
                    if math.hypot(player.x - proj["x"], player.y - proj["y"]) < 22:
                        if player.take_damage(1): random.choice(DRAGON_SOUNDS).play()
                        proj["alive"] = False
                if all_dead: self.timer = 0

            elif self.pattern == "fire_wall":
                self.data["wall_x"] -= 4.0
                wx = self.data["wall_x"]; gy = self.data["gap_y"]; gh = self.data["gap_h"]
                if abs(player.x - wx) < 24:
                    if not (gy - gh // 2 < player.y < gy + gh // 2):
                        if player.take_damage(2): random.choice(DRAGON_SOUNDS).play()
                if wx < -20: self.timer = 0

            elif self.pattern == "lava_zone":
                all_done = True
                for z in self.data["zones"]:
                    if z["fuse"] > 0:
                        z["fuse"] -= 1; all_done = False
                    elif z["erupt"] < 35:
                        z["erupt"] += 1; all_done = False
                        cx = z["x"] + z["w"] // 2; cy = z["y"] + z["h"] // 2
                        if abs(player.x - cx) < z["w"] // 2 + 13 and abs(player.y - cy) < z["h"] // 2 + 13:
                            if player.take_damage(1): random.choice(DRAGON_SOUNDS).play()
                if all_done: self.timer = 0

            elif self.pattern == "flame_counter":
                if not self.data["charging"]:
                    dx = player.x - self.x; dy = player.y - self.y
                    dist = math.hypot(dx, dy) or 1
                    self.data["charge_dir"] = (dx / dist, dy / dist)
                    self.data["charging"] = True
                cdx, cdy = self.data["charge_dir"]
                self.x = max(self.size, min(WIDTH - self.size, self.x + cdx * 13))
                self.y = max(self.size, min(HEIGHT - self.size, self.y + cdy * 13))
                self.data["trail"].append({"x": float(self.x), "y": float(self.y), "life": 40})
                for t in self.data["trail"]:
                    t["life"] -= 1
                    if math.hypot(player.x - t["x"], player.y - t["y"]) < 22:
                        if player.take_damage(1): random.choice(DRAGON_SOUNDS).play()
                self.data["trail"] = [t for t in self.data["trail"] if t["life"] > 0]
                if self.get_rect().colliderect(player.get_rect()):
                    if player.take_damage(2): random.choice(DRAGON_SOUNDS).play()
                    self.timer = 0

            elif self.pattern == "falling_rocks":
                all_done = True
                for r in self.data["rocks"]:
                    if not r["alive"]: continue
                    if r["delay"] > 0:
                        r["delay"] -= 1; all_done = False; continue
                    all_done = False
                    r["y"] += 11
                    if math.hypot(player.x - r["x"], player.y - r["y"]) < 30:
                        if player.take_damage(1): random.choice(DRAGON_SOUNDS).play()
                        r["alive"] = False
                    elif r["y"] > HEIGHT + 30:
                        r["alive"] = False
                if all_done: self.timer = 0

            elif self.pattern == "breath_sweep":
                self.data["angle"] += self.data["sweep_speed"]
                angle = self.data["angle"]
                bx = math.cos(angle); by = math.sin(angle)
                dx = player.x - self.x; dy = player.y - self.y
                dot = dx * bx + dy * by
                if dot > 0 and abs(dx * (-by) + dy * bx) < 32 and dot < 700:
                    if player.take_damage(1): random.choice(DRAGON_SOUNDS).play()
                if self.data["angle"] >= math.pi / 2:
                    self.timer = 0

            elif self.pattern == "tail_wide":
                if "face_dx" not in self.data:
                    dx = player.x - self.x; dy = player.y - self.y
                    dist = math.hypot(dx, dy) or 1
                    self.data["face_dx"] = dx / dist; self.data["face_dy"] = dy / dist
                fdx = self.data["face_dx"]; fdy = self.data["face_dy"]
                dx = player.x - self.x; dy = player.y - self.y
                dist = math.hypot(dx, dy) or 1
                if 0 < dist < 290:
                    dot = (dx / dist) * fdx + (dy / dist) * fdy
                    if dot > math.cos(math.radians(100)):
                        if player.take_damage(1): random.choice(DRAGON_SOUNDS).play()

            elif self.pattern == "fire_ring":
                if not self.data["inited"]:
                    self.data.update({"ring_x": float(player.x), "ring_y": float(player.y), "inited": True})
                self.data["radius"] -= 2.5
                r = self.data["radius"]
                dist = math.hypot(player.x - self.data["ring_x"], player.y - self.data["ring_y"])
                if r > 0 and abs(dist - r) < 26:
                    if player.take_damage(1): random.choice(DRAGON_SOUNDS).play()
                if r <= 0: self.timer = 0

            elif self.pattern == "spine_fan":
                all_dead = True
                for proj in self.data["projs"]:
                    if not proj["alive"]: continue
                    all_dead = False
                    proj["x"] += proj["vx"]; proj["y"] += proj["vy"]
                    if proj["x"] < -10 or proj["x"] > WIDTH + 10 or proj["y"] < -10 or proj["y"] > HEIGHT + 10:
                        proj["alive"] = False; continue
                    if math.hypot(player.x - proj["x"], player.y - proj["y"]) < 20:
                        if player.take_damage(1): random.choice(DRAGON_SOUNDS).play()
                        proj["alive"] = False
                if all_dead: self.timer = 0

            if self.timer <= 0:
                self.state = "vulnerable"
                self.timer = 90
                self.data = {}

        elif self.state == "vulnerable":
            self.timer -= 1
            if self.timer <= 0:
                self.state = "idle"
                self.timer = 50

    def take_damage(self, amount):
        if self.is_vulnerable():
            self.hp -= amount

    def draw(self, small_font):
        sprite = pygame.transform.scale(DRAGON_IMAGE, (self.size, self.size))
        if self.is_vulnerable():
            sprite = sprite.copy()
            sprite.fill((255, 230, 80, 0), special_flags=pygame.BLEND_RGBA_ADD)
        screen.blit(sprite, (self.x - self.size // 2, self.y - self.size // 2))

        if self.pattern == "fire_breath" and self.state in ("telegraph", "active"):
            col = RED if self.state == "active" else (120, 40, 40)
            pygame.draw.rect(screen, col, pygame.Rect(0, self.data["band_y"] - 35, WIDTH, 70))

        if self.pattern == "tail_swipe" and self.state in ("telegraph", "windup", "active"):
            col = RED if self.state == "active" else (120, 40, 40)
            pygame.draw.circle(screen, col, (int(self.x), int(self.y)), 140, 4)

        if self.pattern == "fireball_rain" and self.state in ("telegraph", "active"):
            for p in self.data.get("points", []):
                c = RED if p[2] <= 0 else (120, 40, 40)
                pygame.draw.circle(screen, c, (p[0], p[1]), 45, 0 if p[2] <= 0 else 3)

        if self.pattern in ("fan_fire", "spine_fan") and "aim_angle" in self.data:
            base = self.data["aim_angle"]
            span = 60 if self.pattern == "fan_fire" else 15
            col = (200, 80, 20) if self.state == "telegraph" else (255, 110, 0)
            for off in (-math.radians(span), math.radians(span)):
                pygame.draw.line(screen, col, (int(self.x), int(self.y)),
                                 (int(self.x + math.cos(base + off) * 260), int(self.y + math.sin(base + off) * 260)), 2)
            if self.state == "telegraph":
                pygame.draw.line(screen, (255, 60, 0), (int(self.x), int(self.y)),
                                 (int(self.x + math.cos(base) * 260), int(self.y + math.sin(base) * 260)), 2)
        for pat in ("fan_fire", "spine_fan", "triple_fireball"):
            if self.pattern == pat and self.state == "active":
                for proj in self.data.get("projs", []):
                    if proj["alive"]:
                        pygame.draw.circle(screen, (255, 140, 0), (int(proj["x"]), int(proj["y"])), 9)
                        pygame.draw.circle(screen, (255, 220, 80), (int(proj["x"]), int(proj["y"])), 4)

        if self.pattern == "cross_gust":
            if self.state == "telegraph":
                d = self.data.get("dir", -1)
                pygame.draw.line(screen, (200, 80, 20), (int(self.x), int(self.y)),
                                 (60 if d < 0 else WIDTH - 60, int(self.y)), 4)
            elif self.state == "active":
                d = self.data.get("dir", -1)
                for i in range(1, 4):
                    tx = int(self.x - d * i * 22)
                    pygame.draw.rect(screen, (200, 80, 20),
                                     pygame.Rect(tx - self.size // 2, int(self.y) - self.size // 2, self.size, self.size),
                                     max(1, 3 - i))

        if self.pattern == "fire_wall" and "wall_x" in self.data:
            wx = int(self.data["wall_x"]); gy = self.data["gap_y"]; gh = self.data["gap_h"]
            col = RED if self.state == "active" else (150, 50, 20)
            if wx < WIDTH + 20:
                if gy - gh // 2 > 0:
                    pygame.draw.rect(screen, col, pygame.Rect(wx - 15, 0, 30, gy - gh // 2))
                if gy + gh // 2 < HEIGHT:
                    pygame.draw.rect(screen, col, pygame.Rect(wx - 15, gy + gh // 2, 30, HEIGHT - gy - gh // 2))
                pygame.draw.rect(screen, (255, 200, 0), pygame.Rect(wx - 15, gy - gh // 2, 30, gh), 2)

        if self.pattern == "lava_zone" and self.state in ("telegraph", "active"):
            for z in self.data.get("zones", []):
                r = pygame.Rect(z["x"], z["y"], z["w"], z["h"])
                if z["fuse"] > 0:
                    pygame.draw.rect(screen, (150, 30, 0), r, 3)
                else:
                    intensity = min(255, z["erupt"] * 8)
                    pygame.draw.rect(screen, (intensity, max(0, intensity - 100), 0), r)

        if self.pattern == "flame_counter" and self.state == "active":
            for t in self.data.get("trail", []):
                ratio = t["life"] / 40
                pygame.draw.circle(screen, (int(255 * ratio), int(100 * ratio), 0),
                                   (int(t["x"]), int(t["y"])), max(4, int(14 * ratio)))

        if self.pattern == "falling_rocks" and self.state in ("telegraph", "active"):
            for r in self.data.get("rocks", []):
                if not r["alive"]: continue
                if r["delay"] > 0:
                    pygame.draw.line(screen, (180, 50, 20), (int(r["x"]), 5), (int(r["x"]), 35), 4)
                else:
                    pygame.draw.circle(screen, (180, 80, 20), (int(r["x"]), int(r["y"])), 22)
                    pygame.draw.circle(screen, RED, (int(r["x"]), int(r["y"])), 22, 3)

        if self.pattern == "breath_sweep" and "angle" in self.data:
            angle = self.data["angle"]
            ex = int(self.x + math.cos(angle) * 680); ey = int(self.y + math.sin(angle) * 680)
            col = (255, 100, 0) if self.state == "active" else (180, 60, 20)
            pygame.draw.line(screen, col, (int(self.x), int(self.y)), (ex, ey),
                             34 if self.state == "active" else 3)

        if self.pattern == "tail_wide" and self.state in ("telegraph", "windup", "active"):
            col = RED if self.state == "active" else (120, 40, 40)
            pygame.draw.circle(screen, col, (int(self.x), int(self.y)), 290, 3)

        if self.pattern == "fire_ring" and "ring_x" in self.data and self.data["radius"] > 0:
            r = int(self.data["radius"])
            col = (255, 140, 0) if self.state == "active" else (150, 50, 0)
            pygame.draw.circle(screen, col, (int(self.data["ring_x"]), int(self.data["ring_y"])), r, max(4, r // 8))

        bar_w = 220
        pygame.draw.rect(screen, (60, 60, 60), (WIDTH // 2 - bar_w // 2, 16, bar_w, 16))
        pygame.draw.rect(screen, RED, (WIDTH // 2 - bar_w // 2, 16, int(bar_w * max(self.hp, 0) / self.max_hp), 16))
        name_text = small_font.render(self.name, True, WHITE)
        screen.blit(name_text, (WIDTH // 2 - name_text.get_width() // 2, 34))


class KnightBoss:
    """두 번째 보스: 무적의 기사. 방패 돌진/연속 베기(근접)와 마법 검기(원거리)를 사용한다."""

    name = "KNIGHT"

    def __init__(self):
        self.x = WIDTH - 130
        self.y = HEIGHT // 2
        self.size = 90
        self.hp = 240
        self.max_hp = 240
        self.state = "idle"
        self.timer = 50
        self.pattern = None
        self.data = {}
        self.wander_dir = (0, 0)
        self.wander_timer = 0

    def get_rect(self):
        return pygame.Rect(self.x - self.size // 2, self.y - self.size // 2, self.size, self.size)

    def is_vulnerable(self):
        return self.state == "vulnerable"

    def start_pattern(self):
        self.pattern = random.choice([
            "shield_charge", "combo_slash", "magic_sword_energy", "knight_charge",
            "sword_shockwave", "triple_slash", "blade_whip", "teleport_slam",
            "shield_wall", "cross_blade", "throw_sword", "pull_thrust",
            "spin_chase", "greatsword_arc",
        ])
        self.state = "telegraph"
        self.data = {}
        if self.pattern == "shield_charge":
            self.timer = 35
        elif self.pattern == "combo_slash":
            self.timer = 35
        elif self.pattern == "knight_charge":
            self.data["tele_target"] = None
            self.timer = 45
        elif self.pattern == "magic_sword_energy":
            self.timer = 45
        elif self.pattern == "sword_shockwave":
            self.data.update({"wave_dist": 0.0, "boss_x": 0.0, "boss_y": 0.0})
            self.timer = 40
        elif self.pattern == "triple_slash":
            self.data.update({"slashes": 3, "slash_state": None, "phase_timer": 0})
            self.timer = 35
        elif self.pattern == "blade_whip":
            self.data.update({"angle": 0.0})
            self.timer = 40
        elif self.pattern == "teleport_slam":
            self.data.update({"tgt": (0.0, 0.0), "slammed": False, "slam_r": 0})
            self.timer = 40
        elif self.pattern == "shield_wall":
            self.data.update({"wall_x": 0.0})
            self.timer = 40
        elif self.pattern == "cross_blade":
            self.data["projs"] = []
            self.timer = 35
        elif self.pattern == "throw_sword":
            self.data.update({"sx": 0.0, "sy": 0.0, "vx": 0.0, "vy": 0.0,
                              "returning": False, "travel": 0, "alive": True, "tgt": (0.0, 0.0)})
            self.timer = 35
        elif self.pattern == "pull_thrust":
            self.data.update({"px": 0.0, "py": 0.0, "vx": 0.0, "vy": 0.0, "alive": True, "hit": False})
            self.timer = 35
        elif self.pattern == "spin_chase":
            self.data.update({"rot": 0.0})
            self.timer = 35
        elif self.pattern == "greatsword_arc":
            self.data.update({"face_dx": 0.0, "face_dy": 0.0})
            self.timer = 40

    def update(self, player):
        melee_p = self.pattern in ("shield_charge", "combo_slash")
        busy = (
            (melee_p and self.state in ("windup", "active")) or
            (self.pattern == "knight_charge" and self.state in ("telegraph", "active")) or
            (self.pattern in ("triple_slash", "spin_chase") and self.state == "active") or
            (self.pattern == "greatsword_arc" and self.state in ("windup", "active")) or
            (self.pattern == "sword_shockwave" and self.state == "active")
        )
        if not busy:
            wander(self, WIDTH * 0.55, WIDTH - 70)

        if self.state == "idle":
            self.timer -= 1
            if self.timer <= 0:
                self.start_pattern()

        elif self.state == "telegraph":
            self.timer -= 1
            if self.pattern == "knight_charge":
                self.data["tele_target"] = (player.x, player.y)
            if self.pattern in ("teleport_slam", "throw_sword", "pull_thrust"):
                self.data["tgt"] = (player.x, player.y)
            if self.pattern == "greatsword_arc":
                dx = player.x - self.x; dy = player.y - self.y
                dist = math.hypot(dx, dy) or 1
                self.data["face_dx"] = dx / dist; self.data["face_dy"] = dy / dist
            if self.timer <= 0:
                if melee_p:
                    teleport_near(self, player)
                    self.state = "windup"
                    self.timer = 60
                elif self.pattern == "greatsword_arc":
                    teleport_near(self, player)
                    self.state = "windup"
                    self.timer = 50
                elif self.pattern == "knight_charge":
                    dx = player.x - self.x; dy = player.y - self.y
                    dist = math.hypot(dx, dy) or 1
                    self.data["charge_dir"] = (dx / dist, dy / dist)
                    self.data["hit_player"] = False
                    self.state = "active"; self.timer = 55
                elif self.pattern == "magic_sword_energy":
                    dx, dy = player.x - self.x, player.y - self.y
                    dist = math.hypot(dx, dy) or 1
                    direction = (dx / dist, dy / dist)
                    perp = (-direction[1], direction[0])
                    self.data["proj"] = {"origin": (self.x, self.y), "dir": direction,
                                         "perp": perp, "t": 0, "pos": (self.x, self.y)}
                    self.state = "active"; self.timer = 70
                elif self.pattern == "sword_shockwave":
                    self.data.update({"wave_dist": 0.0, "boss_x": float(self.x), "boss_y": float(self.y)})
                    self.state = "active"; self.timer = 80
                elif self.pattern == "triple_slash":
                    teleport_near(self, player)
                    self.data["slash_state"] = "windup"
                    self.data["phase_timer"] = 22
                    self.state = "active"; self.timer = 300
                elif self.pattern == "blade_whip":
                    self.state = "active"; self.timer = 110
                elif self.pattern == "teleport_slam":
                    tx, ty = self.data["tgt"]
                    self.x = max(self.size, min(WIDTH - self.size, tx))
                    self.y = max(self.size, min(HEIGHT - self.size, ty))
                    self.data["slam_r"] = 0; self.data["slammed"] = True
                    self.state = "active"; self.timer = 45
                elif self.pattern == "shield_wall":
                    self.data["wall_x"] = max(50.0, self.x - 200.0)
                    self.state = "active"; self.timer = 85
                elif self.pattern == "cross_blade":
                    self.data["projs"] = [
                        {"x": float(self.x), "y": float(self.y), "vx": ddx * 8.0, "vy": ddy * 8.0, "alive": True}
                        for ddx, ddy in [(0, -1), (0, 1), (-1, 0), (1, 0)]
                    ]
                    self.state = "active"; self.timer = 110
                elif self.pattern == "throw_sword":
                    tx, ty = self.data["tgt"]
                    dx = tx - self.x; dy = ty - self.y
                    dist = math.hypot(dx, dy) or 1
                    self.data.update({"sx": float(self.x), "sy": float(self.y),
                                      "vx": dx / dist * 11.0, "vy": dy / dist * 11.0,
                                      "returning": False, "travel": 0, "alive": True})
                    self.state = "active"; self.timer = 190
                elif self.pattern == "pull_thrust":
                    tx, ty = self.data["tgt"]
                    dx = tx - self.x; dy = ty - self.y
                    dist = math.hypot(dx, dy) or 1
                    self.data.update({"px": float(self.x), "py": float(self.y),
                                      "vx": dx / dist * 14.0, "vy": dy / dist * 14.0,
                                      "alive": True, "hit": False})
                    self.state = "active"; self.timer = 80
                elif self.pattern == "spin_chase":
                    self.state = "active"; self.timer = 95
                else:
                    self.state = "active"; self.timer = 50

        elif self.state == "windup":
            self.timer -= 1
            if self.timer <= 0:
                self.state = "active"
                self.timer = {"shield_charge": 25, "combo_slash": 45,
                               "greatsword_arc": 22}.get(self.pattern, 20)

        elif self.state == "active":
            self.timer -= 1
            if self.pattern == "shield_charge":
                if in_cardinal_wedge(self, player, 170):
                    if player.take_damage(1): random.choice(SWORD_SOUNDS).play()
            elif self.pattern == "combo_slash":
                if in_cardinal_wedge(self, player, 190):
                    if player.take_damage(1): random.choice(SWORD_SOUNDS).play()
            elif self.pattern == "knight_charge":
                if not self.data.get("hit_player"):
                    cdx, cdy = self.data["charge_dir"]
                    self.x += cdx * 22; self.y += cdy * 22
                    out_x = self.x <= self.size or self.x >= WIDTH - self.size
                    out_y = self.y <= self.size or self.y >= HEIGHT - self.size
                    self.x = max(self.size, min(WIDTH - self.size, self.x))
                    self.y = max(self.size, min(HEIGHT - self.size, self.y))
                    if out_x or out_y:
                        self.timer = 0
                    elif self.get_rect().colliderect(player.get_rect()):
                        if player.take_damage(2):
                            random.choice(SWORD_SOUNDS).play()
                            new_px = player.x + cdx * 30; new_py = player.y + cdy * 30
                            cl_x = max(player.size, min(WIDTH - player.size, new_px))
                            cl_y = max(player.size, min(HEIGHT - player.size, new_py))
                            if cl_x != new_px or cl_y != new_py:
                                player.wall_hit_shake = True
                            player.x = cl_x; player.y = cl_y
                        self.data["hit_player"] = True; self.timer = 0
            elif self.pattern == "magic_sword_energy":
                proj = self.data["proj"]
                proj["t"] += 1
                ox, oy = proj["origin"]; dx, dy = proj["dir"]; px, py = proj["perp"]
                wave = math.sin(proj["t"] * 0.2) * 30
                x = ox + dx * 4 * proj["t"] + px * wave
                y = oy + dy * 4 * proj["t"] + py * wave
                proj["pos"] = (x, y)
                if math.hypot(player.x - x, player.y - y) < 26:
                    player.take_damage(1)

            # === NEW KNIGHT PATTERNS ===
            elif self.pattern == "sword_shockwave":
                self.data["wave_dist"] += 8.0
                wd = self.data["wave_dist"]
                bx = self.data["boss_x"]; by = self.data["boss_y"]
                for wx in (bx - wd, bx + wd):
                    if abs(player.x - wx) < 28 and abs(player.y - by) < 65:
                        if player.take_damage(1): random.choice(SWORD_SOUNDS).play()

            elif self.pattern == "triple_slash":
                d = self.data
                d["phase_timer"] -= 1
                if d["slash_state"] == "windup" and d["phase_timer"] <= 0:
                    d["slash_state"] = "strike"; d["phase_timer"] = 18
                elif d["slash_state"] == "strike":
                    if math.hypot(player.x - self.x, player.y - self.y) < 170:
                        if player.take_damage(1): random.choice(SWORD_SOUNDS).play()
                    if d["phase_timer"] <= 0:
                        d["slashes"] -= 1
                        if d["slashes"] > 0:
                            teleport_near(self, player)
                            d["slash_state"] = "windup"; d["phase_timer"] = 22
                        else:
                            self.timer = 0

            elif self.pattern == "blade_whip":
                self.data["angle"] += 0.10
                a0 = self.data["angle"]
                for i in range(6):
                    a = a0 + i * math.pi / 3
                    bx = self.x + math.cos(a) * 120; by = self.y + math.sin(a) * 120
                    if math.hypot(player.x - bx, player.y - by) < 20:
                        if player.take_damage(1): random.choice(SWORD_SOUNDS).play()

            elif self.pattern == "teleport_slam":
                if self.data["slammed"]:
                    self.data["slam_r"] += 4
                    sr = self.data["slam_r"]
                    dist = math.hypot(player.x - self.x, player.y - self.y)
                    if dist < sr + 14:
                        if player.take_damage(2): random.choice(SWORD_SOUNDS).play()
                    if sr > 90: self.timer = 0

            elif self.pattern == "shield_wall":
                wx = self.data["wall_x"]
                wall_rect = pygame.Rect(int(wx) - 18, 20, 36, HEIGHT - 40)
                if player.dashing and player.get_rect().colliderect(wall_rect):
                    if player.take_damage(2):
                        random.choice(SWORD_SOUNDS).play()
                        player.knockback_vx = -14.0 if player.x > wx else 14.0
                        player.dashing = False

            elif self.pattern == "cross_blade":
                all_dead = True
                for proj in self.data["projs"]:
                    if not proj["alive"]: continue
                    all_dead = False
                    proj["x"] += proj["vx"]; proj["y"] += proj["vy"]
                    if proj["x"] < -10 or proj["x"] > WIDTH + 10 or proj["y"] < -10 or proj["y"] > HEIGHT + 10:
                        proj["alive"] = False; continue
                    if math.hypot(player.x - proj["x"], player.y - proj["y"]) < 22:
                        if player.take_damage(1): random.choice(SWORD_SOUNDS).play()
                        proj["alive"] = False
                if all_dead: self.timer = 0

            elif self.pattern == "throw_sword":
                d = self.data
                if d["alive"]:
                    d["sx"] += d["vx"]; d["sy"] += d["vy"]; d["travel"] += 1
                    if not d["returning"] and d["travel"] > 55:
                        d["returning"] = True
                        dx = self.x - d["sx"]; dy = self.y - d["sy"]
                        dist = math.hypot(dx, dy) or 1
                        d["vx"] = dx / dist * 13; d["vy"] = dy / dist * 13
                    if d["returning"] and math.hypot(d["sx"] - self.x, d["sy"] - self.y) < 30:
                        d["alive"] = False; self.timer = 0
                    if math.hypot(player.x - d["sx"], player.y - d["sy"]) < 22:
                        if player.take_damage(1): random.choice(SWORD_SOUNDS).play()

            elif self.pattern == "pull_thrust":
                d = self.data
                if d["alive"] and not d["hit"]:
                    d["px"] += d["vx"]; d["py"] += d["vy"]
                    if d["px"] < -10 or d["px"] > WIDTH + 10 or d["py"] < -10 or d["py"] > HEIGHT + 10:
                        d["alive"] = False
                    elif math.hypot(player.x - d["px"], player.y - d["py"]) < 22:
                        if player.take_damage(1):
                            random.choice(SWORD_SOUNDS).play()
                            dx = self.x - player.x; dy = self.y - player.y
                            dist = math.hypot(dx, dy) or 1
                            pull = max(0.0, dist - 80)
                            player.x = max(player.size, min(WIDTH - player.size, player.x + dx / dist * pull))
                            player.y = max(player.size, min(HEIGHT - player.size, player.y + dy / dist * pull))
                        d["hit"] = True; d["alive"] = False

            elif self.pattern == "spin_chase":
                self.data["rot"] += 0.14
                dx = player.x - self.x; dy = player.y - self.y
                dist = math.hypot(dx, dy) or 1
                self.x = max(self.size, min(WIDTH - self.size, self.x + dx / dist * 2.0))
                self.y = max(self.size, min(HEIGHT - self.size, self.y + dy / dist * 2.0))
                if math.hypot(player.x - self.x, player.y - self.y) < self.size // 2 + 35 + player.size // 2:
                    if player.take_damage(1): random.choice(SWORD_SOUNDS).play()

            elif self.pattern == "greatsword_arc":
                fdx = self.data["face_dx"]; fdy = self.data["face_dy"]
                dx = player.x - self.x; dy = player.y - self.y
                dist = math.hypot(dx, dy) or 1
                if 0 < dist < 230:
                    dot = (dx / dist) * fdx + (dy / dist) * fdy
                    if dot > math.cos(math.radians(100)):
                        if player.take_damage(2): random.choice(SWORD_SOUNDS).play()

            if self.timer <= 0:
                self.state = "vulnerable"
                self.timer = 90
                self.data = {}

        elif self.state == "vulnerable":
            self.timer -= 1
            if self.timer <= 0:
                self.state = "idle"
                self.timer = 50

    def take_damage(self, amount):
        if self.is_vulnerable():
            self.hp -= amount

    def draw(self, small_font):
        sprite = pygame.transform.scale(KNIGHT_IMAGE, (self.size, self.size))
        if self.is_vulnerable():
            sprite = sprite.copy()
            sprite.fill((255, 230, 80, 0), special_flags=pygame.BLEND_RGBA_ADD)
        screen.blit(sprite, (self.x - self.size // 2, self.y - self.size // 2))

        if self.pattern == "shield_charge" and self.state in ("telegraph", "windup", "active"):
            col = RED if self.state == "active" else (120, 40, 40)
            for d in CARDINAL_DIRS:
                pygame.draw.polygon(screen, col, wedge_points(self.x, self.y, d, 170), 3)
        if self.pattern == "combo_slash" and self.state in ("telegraph", "windup", "active"):
            col = RED if self.state == "active" else (120, 40, 40)
            for d in CARDINAL_DIRS:
                pygame.draw.polygon(screen, col, wedge_points(self.x, self.y, d, 190), 3)
        if self.pattern == "magic_sword_energy" and self.state == "active":
            x, y = self.data["proj"]["pos"]
            pygame.draw.circle(screen, RED, (int(x), int(y)), 14)
        if self.pattern == "knight_charge":
            if self.state == "telegraph" and self.data.get("tele_target"):
                tx, ty = self.data["tele_target"]
                pygame.draw.line(screen, (180, 50, 50), (int(self.x), int(self.y)), (int(tx), int(ty)), 3)
                pygame.draw.circle(screen, (180, 50, 50), (int(tx), int(ty)), 10, 2)
            elif self.state == "active" and "charge_dir" in self.data:
                cdx, cdy = self.data["charge_dir"]
                pygame.draw.line(screen, RED, (int(self.x), int(self.y)),
                                 (int(self.x + cdx * 200), int(self.y + cdy * 200)), 4)

        # === NEW KNIGHT DRAW ===
        if self.pattern == "sword_shockwave" and self.state in ("telegraph", "active") and "boss_x" in self.data:
            wd = int(self.data.get("wave_dist", 0))
            bx = int(self.data["boss_x"]); by = int(self.data["boss_y"])
            col = RED if self.state == "active" else (120, 40, 40)
            for wx in (bx - wd, bx + wd):
                pygame.draw.line(screen, col, (wx, by - 65), (wx, by + 65), 6)

        if self.pattern == "triple_slash" and self.state == "active":
            col = RED if self.data.get("slash_state") == "strike" else (120, 40, 40)
            pygame.draw.circle(screen, col, (int(self.x), int(self.y)), 170, 3)

        if self.pattern == "blade_whip" and self.state in ("telegraph", "active"):
            a0 = self.data.get("angle", 0)
            col = RED if self.state == "active" else (120, 40, 40)
            for i in range(6):
                a = a0 + i * math.pi / 3
                bx = int(self.x + math.cos(a) * 120); by = int(self.y + math.sin(a) * 120)
                pygame.draw.circle(screen, col, (bx, by), 13)

        if self.pattern == "teleport_slam" and self.state == "active" and self.data.get("slammed"):
            sr = self.data.get("slam_r", 0)
            if sr > 0:
                pygame.draw.circle(screen, RED, (int(self.x), int(self.y)), sr, 5)

        if self.pattern == "shield_wall" and self.state in ("telegraph", "active") and "wall_x" in self.data:
            wx = int(self.data["wall_x"])
            col = (200, 130, 0) if self.state == "active" else (120, 80, 0)
            pygame.draw.rect(screen, col, pygame.Rect(wx - 18, 20, 36, HEIGHT - 40))

        if self.pattern == "cross_blade" and self.state in ("telegraph", "active"):
            for proj in self.data.get("projs", []):
                if proj["alive"]:
                    pygame.draw.circle(screen, (200, 200, 255), (int(proj["x"]), int(proj["y"])), 14)
                    pygame.draw.circle(screen, WHITE, (int(proj["x"]), int(proj["y"])), 8)

        if self.pattern == "throw_sword" and self.state in ("telegraph", "active"):
            if self.data.get("alive"):
                sx, sy = int(self.data.get("sx", self.x)), int(self.data.get("sy", self.y))
                pygame.draw.circle(screen, (220, 200, 100), (sx, sy), 14)
                pygame.draw.circle(screen, WHITE, (sx, sy), 7)

        if self.pattern == "pull_thrust" and self.state in ("telegraph", "active"):
            if self.state == "telegraph":
                if "tgt" in self.data:
                    tx, ty = self.data["tgt"]
                    pygame.draw.line(screen, (180, 180, 60), (int(self.x), int(self.y)), (int(tx), int(ty)), 3)
            elif self.data.get("alive"):
                pygame.draw.circle(screen, YELLOW, (int(self.data.get("px", self.x)), int(self.data.get("py", self.y))), 12)

        if self.pattern == "spin_chase" and self.state in ("telegraph", "active"):
            r = self.size // 2 + 35
            col = RED if self.state == "active" else (120, 40, 40)
            pygame.draw.circle(screen, col, (int(self.x), int(self.y)), r, 3)

        if self.pattern == "greatsword_arc" and self.state in ("telegraph", "windup", "active"):
            fdx = self.data.get("face_dx", 1); fdy = self.data.get("face_dy", 0)
            col = RED if self.state == "active" else (120, 40, 40)
            base = math.atan2(fdy, fdx)
            for off in (-math.radians(100), math.radians(100)):
                ex = int(self.x + math.cos(base + off) * 230)
                ey = int(self.y + math.sin(base + off) * 230)
                pygame.draw.line(screen, col, (int(self.x), int(self.y)), (ex, ey), 3)
            pygame.draw.circle(screen, col, (int(self.x), int(self.y)), 230, 3)

        bar_w = 220
        pygame.draw.rect(screen, (60, 60, 60), (WIDTH // 2 - bar_w // 2, 16, bar_w, 16))
        pygame.draw.rect(screen, RED, (WIDTH // 2 - bar_w // 2, 16, int(bar_w * max(self.hp, 0) / self.max_hp), 16))
        name_text = small_font.render(self.name, True, WHITE)
        screen.blit(name_text, (WIDTH // 2 - name_text.get_width() // 2, 34))


class DemonLordBoss:
    """세 번째 보스: 흑마법사 마왕. HP 320, 공격속도 1.5배.
    체력 50% 이하에서 광폭화(ENRAGED) — 붉게 변하며 빨라짐.
    패턴: 어둠의 화살, 분신술, 지옥의 불꽃, 암흑 장벽, 블랙홀, 어둠의 사슬, 종말의 징벌, (광폭화)콤보."""

    name = "DEMON LORD"

    def __init__(self):
        self.x = WIDTH - 130
        self.y = HEIGHT // 2
        self.size = 100
        self.hp = 500
        self.max_hp = 500
        self.state = "idle"
        self.timer = 33
        self.pattern = None
        self.data = {}
        self.wander_dir = (0, 0)
        self.wander_timer = 0
        self.enraged = False
        self.hit_particles = []

    def get_rect(self):
        return pygame.Rect(self.x - self.size // 2, self.y - self.size // 2, self.size, self.size)

    def is_vulnerable(self):
        return self.state == "vulnerable"

    def start_pattern(self):
        pool = ["shadow_arrow", "mirror_clone", "hellfire",
                "dark_barrier", "black_hole", "shadow_chains", "doomsday_laser",
                "arrow_volley", "laser_grid", "decoy_strike", "spike_floor",
                "strong_pull", "dark_wall_h", "orb_field", "multi_chain",
                "eye_gaze", "shadow_burst"]
        if self.enraged:
            pool.append("enrage_combo")
        self.pattern = random.choice(pool)
        self.state = "telegraph"
        self.data = {}
        self.timer = {
            "shadow_arrow": 27, "mirror_clone": 27, "hellfire": 33,
            "dark_barrier": 27, "black_hole": 23, "shadow_chains": 23,
            "doomsday_laser": 40, "enrage_combo": 27,
            "arrow_volley": 35, "laser_grid": 45, "decoy_strike": 40,
            "spike_floor": 40, "strong_pull": 27, "dark_wall_h": 35,
            "orb_field": 30, "multi_chain": 28, "eye_gaze": 35,
            "shadow_burst": 30,
        }[self.pattern]
        # telegraph 중 draw가 접근하는 값은 여기서 미리 설정
        if self.pattern == "black_hole":
            self.data["cx"] = random.randint(WIDTH // 5, WIDTH // 2)
            self.data["cy"] = random.randint(HEIGHT // 5, 4 * HEIGHT // 5)
        elif self.pattern == "doomsday_laser":
            self.data["side"] = random.choice(["top", "bottom", "left", "right"])
        elif self.pattern == "laser_grid":
            v_xs = sorted(random.sample(range(100, WIDTH // 2 - 30), 3))
            h_ys = sorted(random.sample(range(80, HEIGHT - 80), 3))
            lines = []
            for i, x in enumerate(v_xs):
                lines.append({"type": "v", "pos": x, "delay": i * 20, "active": False, "life": 0})
            for i, y in enumerate(h_ys):
                lines.append({"type": "h", "pos": y, "delay": (i + 3) * 20, "active": False, "life": 0})
            self.data["lines"] = lines
        elif self.pattern == "strong_pull":
            self.data["cx"] = random.randint(WIDTH // 5, WIDTH // 2)
            self.data["cy"] = random.randint(HEIGHT // 5, 4 * HEIGHT // 5)
        elif self.pattern == "orb_field":
            self.data["orbs"] = [{"angle": i * math.pi / 2, "alive": True} for i in range(4)]
            self.data["orb_speed"] = 0.045
            self.data["orb_radius"] = 110
        elif self.pattern == "multi_chain":
            chains = []
            for _ in range(3):
                chains.append({"x": float(random.randint(80, WIDTH // 2)),
                               "y": float(random.randint(80, HEIGHT - 80)),
                               "radius": 50})
            self.data["chains"] = chains
        elif self.pattern == "decoy_strike":
            clones = []
            for i in range(4):
                a = i * math.pi / 2
                cx = max(60, min(WIDTH // 2 - 30, self.x + math.cos(a) * 100))
                cy = max(60, min(HEIGHT - 60, self.y + math.sin(a) * 100))
                clones.append({"x": float(cx), "y": float(cy), "alive": True})
            self.data["clones"] = clones
            self.data["real_idx"] = random.randint(0, 3)
            self.data["dashing"] = False
            self.data["dash_dir"] = (0.0, 0.0)
        elif self.pattern == "spike_floor":
            self.data["danger_y"] = int(HEIGHT * 0.6)
        elif self.pattern == "dark_wall_h":
            self.data["wall_y"] = HEIGHT // 2
            self.data["player_above"] = None
        elif self.pattern == "eye_gaze":
            self.data.update({"angle": 0.0, "dmg_timer": 0})
        elif self.pattern in ("shadow_burst", "arrow_volley"):
            self.data["projs"] = []

    def update(self, player):
        # 암흑 장벽 active 중에는 마왕이 움직이지 않음
        if not (self.pattern == "dark_barrier" and self.state == "active"):
            wander(self, WIDTH * 0.55, WIDTH - 70)

        if self.state == "idle":
            self.timer -= 1
            if self.timer <= 0:
                self.start_pattern()

        elif self.state == "telegraph":
            self.timer -= 1
            if self.timer <= 0:
                if self.pattern == "shadow_arrow":
                    dx, dy = player.x - self.x, player.y - self.y
                    dist = math.hypot(dx, dy) or 1
                    self.data["proj"] = {"pos": [self.x, self.y], "dir": (dx / dist, dy / dist)}
                    self.state = "active"
                    self.timer = 60
                elif self.pattern == "mirror_clone":
                    clones = []
                    for _ in range(3):
                        a = random.uniform(0, 2 * math.pi)
                        cx = max(40, min(WIDTH - 40, player.x + math.cos(a) * 160))
                        cy = max(40, min(HEIGHT - 40, player.y + math.sin(a) * 160))
                        clones.append([cx, cy])
                    self.data["clones"] = clones
                    self.state = "windup"
                    self.timer = 30
                elif self.pattern == "hellfire":
                    self.data.update({"cx": self.x, "cy": self.y, "radius": 0})
                    self.state = "active"
                    self.timer = 53
                elif self.pattern == "dark_barrier":
                    self.data["bar_x"] = self.x - 160
                    self.state = "active"
                    self.timer = 67
                elif self.pattern == "black_hole":
                    self.state = "active"
                    self.timer = 67
                elif self.pattern == "shadow_chains":
                    self.data.update({"chain_x": player.x, "chain_y": player.y, "radius": 45})
                    self.state = "active"
                    self.timer = 47
                elif self.pattern == "doomsday_laser":
                    self.state = "active"
                    self.timer = 33
                elif self.pattern == "enrage_combo":
                    dx, dy = player.x - self.x, player.y - self.y
                    dist = math.hypot(dx, dy) or 1
                    self.data["proj"] = {"pos": [self.x, self.y], "dir": (dx / dist, dy / dist)}
                    clones = []
                    for _ in range(3):
                        a = random.uniform(0, 2 * math.pi)
                        cx = max(40, min(WIDTH - 40, player.x + math.cos(a) * 130))
                        cy = max(40, min(HEIGHT - 40, player.y + math.sin(a) * 130))
                        clones.append([cx, cy])
                    self.data["clones"] = clones
                    self.state = "active"
                    self.timer = 47
                # === NEW DEMON LORD PATTERNS ===
                elif self.pattern == "arrow_volley":
                    dx, dy = player.x - self.x, player.y - self.y
                    dist = math.hypot(dx, dy) or 1
                    base_a = math.atan2(dy, dx)
                    self.data["projs"] = [
                        {"x": float(self.x), "y": float(self.y),
                         "vx": math.cos(base_a + (i - 1.5) * 0.22) * 5.5,
                         "vy": math.sin(base_a + (i - 1.5) * 0.22) * 5.5,
                         "alive": True, "homing": True}
                        for i in range(4)
                    ]
                    self.state = "active"
                    self.timer = 120
                elif self.pattern == "laser_grid":
                    self.state = "active"
                    self.timer = 200
                elif self.pattern == "decoy_strike":
                    dx, dy = player.x - self.x, player.y - self.y
                    dist = math.hypot(dx, dy) or 1
                    self.data["dash_dir"] = (dx / dist, dy / dist)
                    self.data["dashing"] = True
                    self.state = "active"
                    self.timer = 80
                elif self.pattern == "spike_floor":
                    self.state = "active"
                    self.timer = 90
                elif self.pattern == "strong_pull":
                    self.state = "active"
                    self.timer = 60
                elif self.pattern == "dark_wall_h":
                    self.data["player_above"] = (player.y < self.data["wall_y"])
                    self.state = "active"
                    self.timer = 80
                elif self.pattern == "orb_field":
                    self.state = "active"
                    self.timer = 130
                elif self.pattern == "multi_chain":
                    self.state = "active"
                    self.timer = 70
                elif self.pattern == "eye_gaze":
                    self.state = "active"
                    self.timer = 90
                elif self.pattern == "shadow_burst":
                    self.data["projs"] = [
                        {"x": float(self.x), "y": float(self.y),
                         "vx": math.cos(i * math.pi / 4) * 6.0,
                         "vy": math.sin(i * math.pi / 4) * 6.0,
                         "alive": True}
                        for i in range(8)
                    ]
                    self.state = "active"
                    self.timer = 100

        elif self.state == "windup":
            self.timer -= 1
            if self.timer <= 0:
                self.state = "active"
                self.timer = 20

        elif self.state == "active":
            self.timer -= 1

            if self.pattern == "shadow_arrow":
                proj = self.data["proj"]
                tx, ty = player.x - proj["pos"][0], player.y - proj["pos"][1]
                tdist = math.hypot(tx, ty) or 1
                dx, dy = proj["dir"]
                nx = dx * 0.92 + tx / tdist * 0.08
                ny = dy * 0.92 + ty / tdist * 0.08
                nlen = math.hypot(nx, ny) or 1
                proj["dir"] = (nx / nlen, ny / nlen)
                proj["pos"][0] += proj["dir"][0] * 5
                proj["pos"][1] += proj["dir"][1] * 5
                if math.hypot(player.x - proj["pos"][0], player.y - proj["pos"][1]) < 24:
                    player.take_damage(1)

            elif self.pattern == "mirror_clone":
                for cx, cy in self.data["clones"]:
                    if math.hypot(player.x - cx, player.y - cy) < 50:
                        player.take_damage(1)

            elif self.pattern == "hellfire":
                self.data["radius"] += 4
                ring_dist = math.hypot(player.x - self.data["cx"], player.y - self.data["cy"])
                if abs(ring_dist - self.data["radius"]) < 22:
                    player.take_damage(1)

            elif self.pattern == "dark_barrier":
                bar_rect = pygame.Rect(int(self.data["bar_x"]), 80, 30, GROUND_Y - 110)
                if player.dashing and player.get_rect().colliderect(bar_rect):
                    if player.take_damage(2):
                        player.knockback_vx = -18.0
                        player.knockback_vy = random.uniform(-4.0, 4.0)
                        player.dashing = False
                        player.dash_timer = 0

            elif self.pattern == "black_hole":
                cx, cy = self.data["cx"], self.data["cy"]
                dx, dy = cx - player.x, cy - player.y
                dist = math.hypot(dx, dy) or 1
                if not player.dashing and dist > 35:
                    pull = min(2.5, 250 / dist)
                    player.x = max(player.size, min(WIDTH - player.size, player.x + dx / dist * pull))
                    player.y = max(player.size, min(HEIGHT - player.size, player.y + dy / dist * pull))
                if dist < 35:
                    player.take_damage(2)

            elif self.pattern == "shadow_chains":
                cx, cy = self.data["chain_x"], self.data["chain_y"]
                if math.hypot(player.x - cx, player.y - cy) < self.data["radius"] and player.bound_timer == 0:
                    player.bound_timer = 60

            elif self.pattern == "doomsday_laser":
                side = self.data["side"]
                in_laser = (
                    (side == "top"    and player.y < HEIGHT // 2) or
                    (side == "bottom" and player.y > HEIGHT // 2) or
                    (side == "left"   and player.x < WIDTH  // 2) or
                    (side == "right"  and player.x > WIDTH  // 2)
                )
                if in_laser:
                    player.take_damage(2)

            elif self.pattern == "enrage_combo":
                proj = self.data["proj"]
                tx, ty = player.x - proj["pos"][0], player.y - proj["pos"][1]
                tdist = math.hypot(tx, ty) or 1
                dx, dy = proj["dir"]
                nx = dx * 0.92 + tx / tdist * 0.08
                ny = dy * 0.92 + ty / tdist * 0.08
                nlen = math.hypot(nx, ny) or 1
                proj["dir"] = (nx / nlen, ny / nlen)
                proj["pos"][0] += proj["dir"][0] * 5
                proj["pos"][1] += proj["dir"][1] * 5
                if math.hypot(player.x - proj["pos"][0], player.y - proj["pos"][1]) < 24:
                    player.take_damage(1)
                for cx, cy in self.data["clones"]:
                    if math.hypot(player.x - cx, player.y - cy) < 50:
                        player.take_damage(1)

            # === NEW DEMON LORD ACTIVE PATTERNS ===
            elif self.pattern == "arrow_volley":
                all_dead = True
                for p in self.data["projs"]:
                    if not p["alive"]:
                        continue
                    all_dead = False
                    tx, ty = player.x - p["x"], player.y - p["y"]
                    tdist = math.hypot(tx, ty) or 1
                    p["vx"] = p["vx"] * 0.93 + tx / tdist * 5.5 * 0.07
                    p["vy"] = p["vy"] * 0.93 + ty / tdist * 5.5 * 0.07
                    p["x"] += p["vx"]; p["y"] += p["vy"]
                    if p["x"] < -10 or p["x"] > WIDTH + 10 or p["y"] < -10 or p["y"] > HEIGHT + 10:
                        p["alive"] = False; continue
                    if math.hypot(player.x - p["x"], player.y - p["y"]) < 22:
                        player.take_damage(1)
                        p["alive"] = False
                if all_dead:
                    self.timer = 0

            elif self.pattern == "laser_grid":
                all_done = True
                for ln in self.data["lines"]:
                    if ln["delay"] > 0:
                        ln["delay"] -= 1
                        all_done = False
                    elif not ln["active"]:
                        ln["active"] = True
                        ln["life"] = 25
                        all_done = False
                    elif ln["life"] > 0:
                        ln["life"] -= 1
                        all_done = False
                        if ln["type"] == "v":
                            if abs(player.x - ln["pos"]) < 26:
                                player.take_damage(2)
                        else:
                            if abs(player.y - ln["pos"]) < 26:
                                player.take_damage(2)
                if all_done:
                    self.timer = 0

            elif self.pattern == "decoy_strike":
                ri = self.data["real_idx"]
                real = self.data["clones"][ri]
                if real["alive"]:
                    ddx, ddy = self.data["dash_dir"]
                    real["x"] += ddx * 14
                    real["y"] += ddy * 14
                    if math.hypot(player.x - real["x"], player.y - real["y"]) < 34:
                        player.take_damage(3)
                        real["alive"] = False
                    elif (real["x"] < -40 or real["x"] > WIDTH + 40 or
                          real["y"] < -40 or real["y"] > HEIGHT + 40):
                        real["alive"] = False

            elif self.pattern == "spike_floor":
                if player.y > self.data["danger_y"]:
                    player.take_damage(1)

            elif self.pattern == "strong_pull":
                cx, cy = self.data["cx"], self.data["cy"]
                dx2, dy2 = cx - player.x, cy - player.y
                dist2 = math.hypot(dx2, dy2) or 1
                if not player.dashing and dist2 > 30:
                    pull = min(10.0, 1000.0 / dist2)
                    player.x = max(player.size, min(WIDTH - player.size, player.x + dx2 / dist2 * pull))
                    player.y = max(player.size, min(HEIGHT - player.size, player.y + dy2 / dist2 * pull))
                if dist2 < 30:
                    player.take_damage(2)

            elif self.pattern == "dark_wall_h":
                wy = self.data["wall_y"]
                pa = self.data["player_above"]
                if pa is True and player.y > wy + 14:
                    player.take_damage(2)
                elif pa is False and player.y < wy - 14:
                    player.take_damage(2)

            elif self.pattern == "orb_field":
                for orb in self.data["orbs"]:
                    if not orb["alive"]:
                        continue
                    orb["angle"] += self.data["orb_speed"]
                    ox = self.x + math.cos(orb["angle"]) * self.data["orb_radius"]
                    oy = self.y + math.sin(orb["angle"]) * self.data["orb_radius"]
                    orb["ox"] = ox; orb["oy"] = oy
                    if player.dashing and math.hypot(player.x - ox, player.y - oy) < 28:
                        orb["alive"] = False
                    elif not player.dashing and math.hypot(player.x - ox, player.y - oy) < 22:
                        player.take_damage(1)

            elif self.pattern == "multi_chain":
                for ch in self.data["chains"]:
                    if math.hypot(player.x - ch["x"], player.y - ch["y"]) < ch["radius"] and player.bound_timer == 0:
                        player.bound_timer = 55

            elif self.pattern == "eye_gaze":
                dx3, dy3 = player.x - self.x, player.y - self.y
                dist3 = math.hypot(dx3, dy3) or 1
                self.data["angle"] = math.atan2(dy3, dx3)
                ang_diff = abs((self.data["angle"] - math.atan2(dy3, dx3) + math.pi) % (2 * math.pi) - math.pi)
                if ang_diff < math.radians(30) and dist3 < 350:
                    player.x = max(player.size, min(WIDTH - player.size, player.x - dx3 / dist3 * 1.8))
                    player.y = max(player.size, min(HEIGHT - player.size, player.y - dy3 / dist3 * 1.8))
                    self.data["dmg_timer"] -= 1
                    if self.data["dmg_timer"] <= 0:
                        player.take_damage(1)
                        self.data["dmg_timer"] = 25
                elif self.data["dmg_timer"] <= 0:
                    self.data["dmg_timer"] = 25

            elif self.pattern == "shadow_burst":
                all_dead = True
                for p in self.data["projs"]:
                    if not p["alive"]:
                        continue
                    all_dead = False
                    p["x"] += p["vx"]; p["y"] += p["vy"]
                    if p["x"] < -10 or p["x"] > WIDTH + 10 or p["y"] < -10 or p["y"] > HEIGHT + 10:
                        p["alive"] = False; continue
                    if math.hypot(player.x - p["x"], player.y - p["y"]) < 20:
                        player.take_damage(1)
                        p["alive"] = False
                if all_dead:
                    self.timer = 0

            if self.timer <= 0:
                self.state = "vulnerable"
                self.timer = 40 if self.enraged else 60
                self.data = {}

        elif self.state == "vulnerable":
            self.timer -= 1
            if self.timer <= 0:
                self.state = "idle"
                self.timer = 22 if self.enraged else 33

        for p in self.hit_particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= 1
        self.hit_particles = [p for p in self.hit_particles if p["life"] > 0]

    def take_damage(self, amount):
        if not self.is_vulnerable():
            return
        self.hp -= amount
        for _ in range(10):
            a = random.uniform(0, 2 * math.pi)
            spd = random.uniform(2, 7)
            self.hit_particles.append({
                "x": float(self.x), "y": float(self.y),
                "vx": math.cos(a) * spd, "vy": math.sin(a) * spd,
                "life": random.randint(15, 25), "max_life": 25,
            })
        if not self.enraged and self.hp <= self.max_hp // 2:
            self.enraged = True

    def draw(self, small_font):
        sprite = pygame.transform.scale(DEMON_LORD_IMAGE, (self.size, self.size))
        if self.enraged:
            tinted = sprite.copy()
            tinted.fill((160, 0, 0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            sprite = tinted
        if self.is_vulnerable():
            tinted = sprite.copy()
            tinted.fill((255, 230, 80, 0), special_flags=pygame.BLEND_RGBA_ADD)
            sprite = tinted
        screen.blit(sprite, (self.x - self.size // 2, self.y - self.size // 2))

        if self.pattern == "shadow_arrow" and self.state == "active":
            x, y = self.data["proj"]["pos"]
            pygame.draw.circle(screen, PURPLE, (int(x), int(y)), 16)

        if self.pattern == "mirror_clone" and self.state in ("windup", "active"):
            color = PURPLE if self.state == "active" else (90, 50, 120)
            for cx, cy in self.data.get("clones", []):
                pygame.draw.circle(screen, color, (int(cx), int(cy)), 50, 0 if self.state == "active" else 3)

        if self.pattern == "hellfire" and self.state == "active":
            pygame.draw.circle(screen, ORANGE,
                               (int(self.data["cx"]), int(self.data["cy"])),
                               int(self.data["radius"]), 6)

        if self.pattern == "dark_barrier" and self.state in ("telegraph", "active"):
            bx = int(self.data.get("bar_x", self.x - 160))
            col = (140, 0, 200) if self.state == "active" else (70, 0, 100)
            pygame.draw.rect(screen, col, pygame.Rect(bx, 80, 30, GROUND_Y - 110))
            pygame.draw.rect(screen, (200, 50, 255), pygame.Rect(bx, 80, 30, GROUND_Y - 110), 3)

        if self.pattern == "black_hole" and self.state in ("telegraph", "active"):
            cx, cy = int(self.data["cx"]), int(self.data["cy"])
            pygame.draw.circle(screen, (10, 0, 20), (cx, cy), 30)
            for r in (30, 55, 85):
                pygame.draw.circle(screen, PURPLE, (cx, cy), r, 3)

        if self.pattern == "shadow_chains" and self.state in ("telegraph", "active") and "chain_x" in self.data:
            cx, cy = int(self.data["chain_x"]), int(self.data["chain_y"])
            r = self.data["radius"]
            if self.state == "telegraph":
                pygame.draw.circle(screen, (50, 0, 50), (cx, cy), r, 3)
            else:
                pygame.draw.circle(screen, PURPLE, (cx, cy), r, 4)
                for i in range(4):
                    a = i * math.pi / 2
                    lx, ly = int(cx + math.cos(a) * r * 0.6), int(cy + math.sin(a) * r * 0.6)
                    pygame.draw.line(screen, PURPLE, (cx, cy), (lx, ly), 3)
                    pygame.draw.circle(screen, (200, 50, 200), (lx, ly), 7)

        if self.pattern == "doomsday_laser" and self.state in ("telegraph", "active"):
            side = self.data["side"]
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            if self.state == "telegraph":
                fill_color = (180, 0, 0, 60)
                line_color = RED
            else:
                fill_color = (80, 0, 120, 180)
                line_color = (200, 50, 255)
            area = {"top": (0, 0, WIDTH, HEIGHT // 2), "bottom": (0, HEIGHT // 2, WIDTH, HEIGHT // 2),
                    "left": (0, 0, WIDTH // 2, HEIGHT), "right": (WIDTH // 2, 0, WIDTH // 2, HEIGHT)}[side]
            pygame.draw.rect(overlay, fill_color, area)
            screen.blit(overlay, (0, 0))
            if side in ("top", "bottom"):
                pygame.draw.line(screen, line_color, (0, HEIGHT // 2), (WIDTH, HEIGHT // 2), 3)
            else:
                pygame.draw.line(screen, line_color, (WIDTH // 2, 0), (WIDTH // 2, HEIGHT), 3)

        if self.pattern == "enrage_combo" and self.state == "active":
            x, y = self.data["proj"]["pos"]
            pygame.draw.circle(screen, PURPLE, (int(x), int(y)), 16)
            for cx, cy in self.data.get("clones", []):
                pygame.draw.circle(screen, PURPLE, (int(cx), int(cy)), 50)

        # === NEW DEMON LORD PATTERN DRAWS ===
        if self.pattern == "arrow_volley" and self.state in ("telegraph", "active"):
            for p in self.data.get("projs", []):
                if p.get("alive", False):
                    pygame.draw.circle(screen, (180, 0, 220), (int(p["x"]), int(p["y"])), 12)
                    pygame.draw.circle(screen, WHITE, (int(p["x"]), int(p["y"])), 5)

        if self.pattern == "laser_grid" and self.state in ("telegraph", "active"):
            for ln in self.data.get("lines", []):
                if ln["delay"] > 0:
                    col = (80, 0, 80)
                    thickness = 1
                elif ln["active"] and ln["life"] > 0:
                    col = (220, 80, 255)
                    thickness = max(2, int(ln["life"] * 0.4))
                else:
                    continue
                if ln["type"] == "v":
                    pygame.draw.line(screen, col, (int(ln["pos"]), 0), (int(ln["pos"]), HEIGHT), thickness)
                else:
                    pygame.draw.line(screen, col, (0, int(ln["pos"])), (WIDTH, int(ln["pos"])), thickness)

        if self.pattern == "decoy_strike" and self.state in ("telegraph", "active"):
            for i, cl in enumerate(self.data.get("clones", [])):
                if not cl.get("alive", True):
                    continue
                col = (160, 0, 200) if self.state == "telegraph" else (200, 40, 255)
                pygame.draw.rect(screen, col,
                                 pygame.Rect(int(cl["x"]) - 20, int(cl["y"]) - 20, 40, 40))
                pygame.draw.rect(screen, WHITE,
                                 pygame.Rect(int(cl["x"]) - 20, int(cl["y"]) - 20, 40, 40), 2)

        if self.pattern == "spike_floor" and self.state in ("telegraph", "active"):
            dy_val = self.data.get("danger_y", int(HEIGHT * 0.6))
            overlay = pygame.Surface((WIDTH, HEIGHT - dy_val), pygame.SRCALPHA)
            alpha = 120 if self.state == "active" else 60
            overlay.fill((200, 50, 0, alpha))
            screen.blit(overlay, (0, dy_val))
            col = (255, 80, 0) if self.state == "active" else (140, 40, 0)
            pygame.draw.line(screen, col, (0, dy_val), (WIDTH, dy_val), 3)
            if self.state == "active":
                spike_count = 12
                sw = WIDTH // spike_count
                for si in range(spike_count):
                    sx = si * sw + sw // 2
                    pts = [(sx - sw // 3, HEIGHT), (sx, dy_val + 10), (sx + sw // 3, HEIGHT)]
                    pygame.draw.polygon(screen, (255, 100, 0), pts)

        if self.pattern == "strong_pull" and self.state in ("telegraph", "active"):
            cx, cy = int(self.data["cx"]), int(self.data["cy"])
            pygame.draw.circle(screen, (5, 0, 10), (cx, cy), 35)
            for r in (35, 65, 100, 140):
                pygame.draw.circle(screen, (180, 0, 255), (cx, cy), r, 2)

        if self.pattern == "dark_wall_h" and self.state in ("telegraph", "active"):
            wy = self.data.get("wall_y", HEIGHT // 2)
            pa = self.data.get("player_above")
            overlay = pygame.Surface((WIDTH, HEIGHT // 2), pygame.SRCALPHA)
            if self.state == "active" and pa is not None:
                danger_overlay = pygame.Surface((WIDTH, HEIGHT // 2), pygame.SRCALPHA)
                danger_overlay.fill((180, 0, 0, 80))
                screen.blit(danger_overlay, (0, wy if pa else 0))
            line_col = (200, 50, 255) if self.state == "active" else (100, 0, 120)
            pygame.draw.line(screen, line_col, (0, wy), (WIDTH, wy), 4)

        if self.pattern == "orb_field" and self.state in ("telegraph", "active"):
            for orb in self.data.get("orbs", []):
                if not orb["alive"]:
                    continue
                ox = self.x + math.cos(orb["angle"]) * self.data.get("orb_radius", 110)
                oy = self.y + math.sin(orb["angle"]) * self.data.get("orb_radius", 110)
                pygame.draw.circle(screen, (220, 60, 255), (int(ox), int(oy)), 18)
                pygame.draw.circle(screen, WHITE, (int(ox), int(oy)), 8)

        if self.pattern == "multi_chain" and self.state in ("telegraph", "active"):
            for ch in self.data.get("chains", []):
                col = (50, 0, 50) if self.state == "telegraph" else PURPLE
                thickness = 2 if self.state == "telegraph" else 4
                pygame.draw.circle(screen, col, (int(ch["x"]), int(ch["y"])), ch["radius"], thickness)
                if self.state == "active":
                    for i in range(4):
                        a = i * math.pi / 2
                        lx = int(ch["x"] + math.cos(a) * ch["radius"] * 0.6)
                        ly = int(ch["y"] + math.sin(a) * ch["radius"] * 0.6)
                        pygame.draw.line(screen, PURPLE, (int(ch["x"]), int(ch["y"])), (lx, ly), 3)
                        pygame.draw.circle(screen, (200, 50, 200), (lx, ly), 6)

        if self.pattern == "eye_gaze" and self.state in ("telegraph", "active"):
            angle = self.data.get("angle", 0.0)
            half = math.radians(30)
            cone_len = 350
            pts = [
                (int(self.x), int(self.y)),
                (int(self.x + math.cos(angle - half) * cone_len),
                 int(self.y + math.sin(angle - half) * cone_len)),
                (int(self.x + math.cos(angle + half) * cone_len),
                 int(self.y + math.sin(angle + half) * cone_len)),
            ]
            cone_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            col_a = 60 if self.state == "telegraph" else 110
            pygame.draw.polygon(cone_surf, (255, 0, 0, col_a), pts)
            screen.blit(cone_surf, (0, 0))
            line_col = (200, 50, 0) if self.state == "active" else (100, 20, 0)
            pygame.draw.line(screen, line_col, pts[0], pts[1], 2)
            pygame.draw.line(screen, line_col, pts[0], pts[2], 2)

        if self.pattern == "shadow_burst" and self.state in ("telegraph", "active"):
            for p in self.data.get("projs", []):
                if p.get("alive", False):
                    pygame.draw.circle(screen, (150, 0, 200), (int(p["x"]), int(p["y"])), 14)
                    pygame.draw.circle(screen, (220, 100, 255), (int(p["x"]), int(p["y"])), 7)

        for p in self.hit_particles:
            ratio = p["life"] / p["max_life"]
            size = max(1, int(6 * ratio))
            pygame.draw.circle(screen, (int(120 * ratio), 0, int(220 * ratio)),
                               (int(p["x"]), int(p["y"])), size)

        bar_w = 220
        pygame.draw.rect(screen, (60, 60, 60), (WIDTH // 2 - bar_w // 2, 16, bar_w, 16))
        bar_col = (255, 80, 0) if self.enraged else RED
        pygame.draw.rect(screen, bar_col,
                         (WIDTH // 2 - bar_w // 2, 16,
                          int(bar_w * max(self.hp, 0) / self.max_hp), 16))
        label = self.name + ("  [ENRAGED]" if self.enraged else "")
        name_text = small_font.render(label, True, WHITE)
        screen.blit(name_text, (WIDTH // 2 - name_text.get_width() // 2, 34))


BOSS_SEQUENCE = [DragonBoss, KnightBoss, DemonLordBoss]
BOSS_NAME_MAP = {
    "드래곤": DragonBoss, "기사": KnightBoss, "마왕": DemonLordBoss,
    "거울속의 나": "OrangeMirrorBoss", "샌즈": "SansBoss",
    "파피루스": "PapyrusBoss", "언다인": "UndyneBoss", "토리엘": "TorielBoss",
    "아스리엘": "AsrielBoss",
}


class OrangeMirrorBoss:
    """히든 보스: 주황색 거울. 주인공과 똑같이 생긴 주황색 사각형.
    패턴: 미러 대쉬, 점프 스탬프, 잔상 폭발, 분열 공격, (각성)오렌지 오버드라이브."""

    name = "???"

    def __init__(self):
        self.size = 26
        self.x = float(WIDTH - 120)
        self.y = float(HEIGHT // 2)
        self.hp = 130
        self.max_hp = 130
        self.state = "idle"
        self.timer = 60
        self.pattern = None
        self.data = {}
        self.enraged = False

    def get_rect(self):
        return pygame.Rect(int(self.x) - self.size // 2, int(self.y) - self.size // 2, self.size, self.size)

    def is_vulnerable(self):
        return self.state == "vulnerable"

    def start_pattern(self):
        pool = ["mirror_dash", "jump_stamp", "phantom_trail", "split_squares",
                "pinball", "trail_bomb", "quad_rush", "shadow_mimic",
                "absorb_shield", "screen_divide", "giant_slam", "fake_charge",
                "burst_spread", "warp_strike"]
        if self.enraged:
            pool.append("orange_overdrive")
        self.pattern = random.choice(pool)
        self.state = "telegraph"
        self.data = {}
        self.timer = {
            "mirror_dash": 30, "jump_stamp": 35, "phantom_trail": 25,
            "split_squares": 30, "orange_overdrive": 20,
            "pinball": 28, "trail_bomb": 25, "quad_rush": 35,
            "shadow_mimic": 25, "absorb_shield": 30, "screen_divide": 30,
            "giant_slam": 40, "fake_charge": 40, "burst_spread": 25,
            "warp_strike": 30,
        }[self.pattern]
        if self.pattern == "screen_divide":
            self.data["danger_top"] = random.choice([True, False])
        elif self.pattern == "giant_slam":
            self.data.update({"phase": "growing", "grow_size": float(self.size),
                              "target_x": 0.0, "target_y": 0.0, "slam_timer": 0})
        elif self.pattern == "shadow_mimic":
            self.data.update({"pos_history": [], "ghost_x": None, "ghost_y": None})
        elif self.pattern == "trail_bomb":
            self.data.update({"bombs": [], "zig_timer": 25, "vx": 0.0, "vy": 0.0})
        elif self.pattern == "warp_strike":
            self.data.update({"projs": [], "warps_left": 3, "warp_cooldown": 0})
        elif self.pattern == "burst_spread":
            self.data["projs"] = []
        elif self.pattern == "fake_charge":
            self.data["projs"] = []

    def update(self, player):
        # 공격 중이 아닐 때 천천히 플레이어 쪽으로 이동
        rising_or_falling = (self.pattern == "jump_stamp" and
                             self.data.get("phase") in ("rising", "falling"))
        if self.state != "vulnerable" and not rising_or_falling:
            dx = player.x - self.x
            dy = player.y - self.y
            dist = math.hypot(dx, dy) or 1
            spd = 1.3 if self.state == "idle" else 0.3
            self.x = max(self.size, min(WIDTH - self.size, self.x + dx / dist * spd))
            self.y = max(self.size, min(HEIGHT - self.size, self.y + dy / dist * spd))

        if self.state == "idle":
            self.timer -= 1
            if self.timer <= 0:
                self.start_pattern()

        elif self.state == "telegraph":
            self.timer -= 1
            if self.timer <= 0:
                if self.pattern == "mirror_dash":
                    self.data.update({"player_was_dashing": False, "counter_dashing": False,
                                      "counter_dash_timer": 0, "dash_dir": (0.0, 0.0)})
                    self.state = "active"
                    self.timer = 130
                elif self.pattern == "jump_stamp":
                    self.data.update({"target_x": float(player.x),
                                      "target_y": float(HEIGHT * 2 // 3),
                                      "phase": "rising", "shockwave_timer": 0})
                    self.state = "active"
                    self.timer = 200
                elif self.pattern == "phantom_trail":
                    self.data.update({"trails": [], "dash_count": 0, "dash_max": 5,
                                      "dash_cooldown": 5, "exploding": False})
                    self.state = "active"
                    self.timer = 280
                elif self.pattern == "split_squares":
                    minis = []
                    for ddx, ddy in [(0, -70), (0, 70), (-70, 0), (70, 0)]:
                        minis.append({"x": float(self.x + ddx), "y": float(self.y + ddy), "alive": True})
                    self.data["minis"] = minis
                    self.state = "active"
                    self.timer = 160
                elif self.pattern == "orange_overdrive":
                    self.data.update({"pos_history": [], "recording": True,
                                      "ghost_idx": 0, "ghost_pos": None, "ghost_active": False})
                    self.state = "active"
                    self.timer = 290
                # === NEW ORANGE MIRROR PATTERNS ===
                elif self.pattern == "pinball":
                    angle = random.uniform(math.pi / 6, math.pi / 3)
                    spd = 9.0
                    sides = random.choice([1, -1])
                    self.data.update({"vx": math.cos(angle) * spd * sides,
                                      "vy": math.sin(angle) * spd})
                    self.state = "active"; self.timer = 180
                elif self.pattern == "trail_bomb":
                    dx, dy = player.x - self.x, player.y - self.y
                    dist = math.hypot(dx, dy) or 1
                    self.data["vx"] = dx / dist * 7.0
                    self.data["vy"] = dy / dist * 7.0
                    self.state = "active"; self.timer = 200
                elif self.pattern == "quad_rush":
                    margin = 50
                    self.data["rushers"] = [
                        {"x": float(WIDTH // 2), "y": float(-margin), "vx": 0.0, "vy": 14.0, "alive": True},
                        {"x": float(WIDTH // 2), "y": float(HEIGHT + margin), "vx": 0.0, "vy": -14.0, "alive": True},
                        {"x": float(-margin), "y": float(HEIGHT // 2), "vx": 14.0, "vy": 0.0, "alive": True},
                        {"x": float(WIDTH + margin), "y": float(HEIGHT // 2), "vx": -14.0, "vy": 0.0, "alive": True},
                    ]
                    self.state = "active"; self.timer = 100
                elif self.pattern == "shadow_mimic":
                    self.state = "active"; self.timer = 250
                elif self.pattern == "absorb_shield":
                    self.state = "active"; self.timer = 100
                elif self.pattern == "screen_divide":
                    self.state = "active"; self.timer = 80
                elif self.pattern == "giant_slam":
                    self.data["target_x"] = float(player.x)
                    self.data["target_y"] = float(player.y)
                    self.state = "active"; self.timer = 230
                elif self.pattern == "fake_charge":
                    dx2, dy2 = player.x - self.x, player.y - self.y
                    d2 = math.hypot(dx2, dy2) or 1
                    base_a = math.atan2(dy2, dx2)
                    self.data["projs"] = [
                        {"x": float(self.x), "y": float(self.y),
                         "vx": math.cos(base_a + (i - 1) * 0.3) * 9.0,
                         "vy": math.sin(base_a + (i - 1) * 0.3) * 9.0,
                         "alive": True}
                        for i in range(3)
                    ]
                    self.state = "active"; self.timer = 100
                elif self.pattern == "burst_spread":
                    self.data["projs"] = [
                        {"x": float(self.x), "y": float(self.y),
                         "vx": math.cos(i * math.pi / 4) * 7.5,
                         "vy": math.sin(i * math.pi / 4) * 7.5,
                         "alive": True}
                        for i in range(8)
                    ]
                    self.state = "active"; self.timer = 100
                elif self.pattern == "warp_strike":
                    corners = [(60.0, 60.0), (float(WIDTH - 60), 60.0),
                               (60.0, float(HEIGHT - 60)), (float(WIDTH - 60), float(HEIGHT - 60))]
                    cx2, cy2 = random.choice(corners)
                    self.x, self.y = cx2, cy2
                    dx3, dy3 = player.x - self.x, player.y - self.y
                    d3 = math.hypot(dx3, dy3) or 1
                    base_a2 = math.atan2(dy3, dx3)
                    self.data["projs"] = [
                        {"x": float(self.x), "y": float(self.y),
                         "vx": math.cos(base_a2 + (i - 1) * 0.3) * 9.0,
                         "vy": math.sin(base_a2 + (i - 1) * 0.3) * 9.0,
                         "alive": True}
                        for i in range(3)
                    ]
                    self.data["warps_left"] = 2
                    self.data["warp_cooldown"] = 55
                    self.state = "active"; self.timer = 150

        elif self.state == "active":
            self.timer -= 1

            if self.pattern == "mirror_dash":
                cur = player.dashing
                if not self.data["player_was_dashing"] and cur:
                    dx = player.x - self.x
                    dy = player.y - self.y
                    dist = math.hypot(dx, dy) or 1
                    self.data["dash_dir"] = (dx / dist, dy / dist)
                    self.data["counter_dashing"] = True
                    self.data["counter_dash_timer"] = 12
                self.data["player_was_dashing"] = cur
                if self.data["counter_dashing"]:
                    ddx, ddy = self.data["dash_dir"]
                    self.x = max(self.size, min(WIDTH - self.size, self.x + ddx * 22))
                    self.y = max(self.size, min(HEIGHT - self.size, self.y + ddy * 22))
                    self.data["counter_dash_timer"] -= 1
                    if self.data["counter_dash_timer"] <= 0:
                        self.data["counter_dashing"] = False
                    if self.get_rect().colliderect(player.get_rect()):
                        if player.take_damage(2, melee=True):
                            pbx = player.x - self.x
                            pby = player.y - self.y
                            pd = math.hypot(pbx, pby) or 1
                            player.knockback_vx = pbx / pd * 18
                            player.knockback_vy = pby / pd * 18
                            player.dashing = False
                            player.dash_timer = 0
                        self.data["counter_dashing"] = False

            elif self.pattern == "jump_stamp":
                phase = self.data.get("phase")
                if phase == "rising":
                    self.y -= 30
                    if self.y < -50:
                        self.x = self.data["target_x"]
                        self.data["phase"] = "falling"
                elif phase == "falling":
                    self.y += 30
                    if self.y >= self.data["target_y"]:
                        self.y = self.data["target_y"]
                        self.data["phase"] = "shockwave"
                        self.data["shockwave_timer"] = 38
                elif phase == "shockwave":
                    self.data["shockwave_timer"] -= 1
                    shock_y = self.data["target_y"]
                    if abs(player.y - shock_y) < 38:
                        player.take_damage(1, melee=True)
                    if self.data["shockwave_timer"] <= 0:
                        self.timer = 0

            elif self.pattern == "phantom_trail":
                if not self.data["exploding"]:
                    self.data["dash_cooldown"] -= 1
                    if self.data["dash_cooldown"] <= 0 and self.data["dash_count"] < self.data["dash_max"]:
                        a = random.uniform(0, 2 * math.pi)
                        old_x, old_y = self.x, self.y
                        self.x = max(self.size, min(WIDTH - self.size, self.x + math.cos(a) * 130))
                        self.y = max(self.size, min(HEIGHT - self.size, self.y + math.sin(a) * 130))
                        fuse = 35 + self.data["dash_count"] * 12
                        self.data["trails"].append({"x": old_x, "y": old_y,
                                                     "fuse": fuse, "exploded": False, "radius": 0})
                        self.data["dash_count"] += 1
                        self.data["dash_cooldown"] = 20
                    elif self.data["dash_count"] >= self.data["dash_max"]:
                        self.data["exploding"] = True
                else:
                    all_done = True
                    for tr in self.data["trails"]:
                        if tr["exploded"]:
                            tr["radius"] += 5
                            dist = math.hypot(player.x - tr["x"], player.y - tr["y"])
                            if abs(dist - tr["radius"]) < 22:
                                player.take_damage(1)
                            if tr["radius"] < 110:
                                all_done = False
                        else:
                            tr["fuse"] -= 1
                            if tr["fuse"] <= 0:
                                tr["exploded"] = True
                            all_done = False
                    if all_done:
                        self.timer = 0

            elif self.pattern == "split_squares":
                all_gone = True
                for mini in self.data["minis"]:
                    if not mini["alive"]:
                        continue
                    all_gone = False
                    ddx = player.x - mini["x"]
                    ddy = player.y - mini["y"]
                    dist = math.hypot(ddx, ddy) or 1
                    mini["x"] += ddx / dist * 4.5
                    mini["y"] += ddy / dist * 4.5
                    mini_rect = pygame.Rect(int(mini["x"]) - 6, int(mini["y"]) - 6, 13, 13)
                    if mini_rect.colliderect(player.get_rect()):
                        if player.take_damage(1):
                            mini["alive"] = False
                if all_gone:
                    self.timer = 0

            elif self.pattern == "orange_overdrive":
                if self.data["recording"]:
                    self.data["pos_history"].append((float(player.x), float(player.y)))
                    if len(self.data["pos_history"]) >= 90:
                        self.data["recording"] = False
                        self.data["ghost_active"] = True
                if self.data["ghost_active"]:
                    idx = self.data["ghost_idx"]
                    if idx < len(self.data["pos_history"]):
                        self.data["ghost_pos"] = self.data["pos_history"][idx]
                        self.data["ghost_idx"] += 1
                        gx, gy = self.data["ghost_pos"]
                        ghost_rect = pygame.Rect(int(gx) - 13, int(gy) - 13, 26, 26)
                        if ghost_rect.colliderect(player.get_rect()):
                            player.take_damage(1)
                    else:
                        self.data["ghost_idx"] = 0  # 루프

            # === NEW ORANGE MIRROR ACTIVE PATTERNS ===
            elif self.pattern == "pinball":
                self.x += self.data["vx"]
                self.y += self.data["vy"]
                if self.x - self.size < 0:
                    self.x = float(self.size)
                    self.data["vx"] = abs(self.data["vx"])
                elif self.x + self.size > WIDTH:
                    self.x = float(WIDTH - self.size)
                    self.data["vx"] = -abs(self.data["vx"])
                if self.y - self.size < 0:
                    self.y = float(self.size)
                    self.data["vy"] = abs(self.data["vy"])
                elif self.y + self.size > HEIGHT:
                    self.y = float(HEIGHT - self.size)
                    self.data["vy"] = -abs(self.data["vy"])
                if self.get_rect().colliderect(player.get_rect()):
                    player.take_damage(2, melee=True)

            elif self.pattern == "trail_bomb":
                self.x = max(self.size, min(WIDTH - self.size, self.x + self.data["vx"]))
                self.y = max(self.size, min(HEIGHT - self.size, self.y + self.data["vy"]))
                if self.x <= self.size or self.x >= WIDTH - self.size:
                    self.data["vx"] *= -1
                if self.y <= self.size or self.y >= HEIGHT - self.size:
                    self.data["vy"] *= -1
                self.data["zig_timer"] -= 1
                if self.data["zig_timer"] <= 0:
                    self.data["bombs"].append({"x": float(self.x), "y": float(self.y),
                                               "fuse": 45, "exploded": False, "radius": 0})
                    self.data["zig_timer"] = 28
                    vx, vy = self.data["vx"], self.data["vy"]
                    self.data["vx"] = -vy * 0.9; self.data["vy"] = vx * 0.9
                for b in self.data["bombs"]:
                    if b["exploded"]:
                        b["radius"] = min(b["radius"] + 6, 100)
                        if math.hypot(player.x - b["x"], player.y - b["y"]) < b["radius"] + 10:
                            player.take_damage(1)
                    else:
                        b["fuse"] -= 1
                        if b["fuse"] <= 0:
                            b["exploded"] = True
                self.data["bombs"] = [b for b in self.data["bombs"]
                                      if not b["exploded"] or b["radius"] < 100]

            elif self.pattern == "quad_rush":
                all_done = True
                for r in self.data["rushers"]:
                    if not r["alive"]:
                        continue
                    all_done = False
                    r["x"] += r["vx"]; r["y"] += r["vy"]
                    r_rect = pygame.Rect(int(r["x"]) - 13, int(r["y"]) - 13, 26, 26)
                    if r_rect.colliderect(player.get_rect()):
                        player.take_damage(2, melee=True)
                        r["alive"] = False
                    elif r["x"] < -80 or r["x"] > WIDTH + 80 or r["y"] < -80 or r["y"] > HEIGHT + 80:
                        r["alive"] = False
                if all_done:
                    self.timer = 0

            elif self.pattern == "shadow_mimic":
                self.data["pos_history"].append((float(player.x), float(player.y)))
                if len(self.data["pos_history"]) > 120:
                    gx, gy = self.data["pos_history"].pop(0)
                    self.data["ghost_x"] = gx
                    self.data["ghost_y"] = gy
                    g_rect = pygame.Rect(int(gx) - 13, int(gy) - 13, 26, 26)
                    if g_rect.colliderect(player.get_rect()):
                        player.take_damage(1)

            elif self.pattern == "absorb_shield":
                if player.dashing and self.get_rect().colliderect(player.get_rect()):
                    if player.take_damage(2, melee=True):
                        pbx, pby = player.x - self.x, player.y - self.y
                        pd = math.hypot(pbx, pby) or 1
                        player.knockback_vx = pbx / pd * 16
                        player.knockback_vy = pby / pd * 16
                        player.dashing = False
                        player.dash_timer = 0

            elif self.pattern == "screen_divide":
                hy = HEIGHT // 2
                if self.data["danger_top"] and player.y < hy:
                    player.take_damage(1)
                elif not self.data["danger_top"] and player.y > hy:
                    player.take_damage(1)

            elif self.pattern == "giant_slam":
                phase = self.data["phase"]
                if phase == "growing":
                    self.data["grow_size"] = min(self.data["grow_size"] + 1.5, self.size * 3)
                    if self.data["grow_size"] >= self.size * 3:
                        self.data["phase"] = "charging"
                elif phase == "charging":
                    ddx2, ddy2 = self.data["target_x"] - self.x, self.data["target_y"] - self.y
                    dist2 = math.hypot(ddx2, ddy2) or 1
                    if dist2 > 15:
                        self.x += ddx2 / dist2 * 12
                        self.y += ddy2 / dist2 * 12
                    else:
                        self.data["phase"] = "slamming"
                        self.data["slam_timer"] = 35
                elif phase == "slamming":
                    self.data["slam_timer"] -= 1
                    gs = int(self.data["grow_size"])
                    slam_rect = pygame.Rect(int(self.x) - gs // 2, int(self.y) - gs // 2, gs, gs)
                    if slam_rect.colliderect(player.get_rect()):
                        player.take_damage(3, melee=True)
                    if self.data["slam_timer"] <= 0:
                        self.data["grow_size"] = float(self.size)
                        self.timer = 0

            elif self.pattern == "fake_charge":
                all_dead = True
                for p in self.data.get("projs", []):
                    if not p["alive"]:
                        continue
                    all_dead = False
                    p["x"] += p["vx"]; p["y"] += p["vy"]
                    if p["x"] < -10 or p["x"] > WIDTH + 10 or p["y"] < -10 or p["y"] > HEIGHT + 10:
                        p["alive"] = False; continue
                    if math.hypot(player.x - p["x"], player.y - p["y"]) < 18:
                        player.take_damage(1)
                        p["alive"] = False
                if all_dead:
                    self.timer = 0

            elif self.pattern == "burst_spread":
                all_dead = True
                for p in self.data.get("projs", []):
                    if not p["alive"]:
                        continue
                    all_dead = False
                    p["x"] += p["vx"]; p["y"] += p["vy"]
                    if p["x"] < -10 or p["x"] > WIDTH + 10 or p["y"] < -10 or p["y"] > HEIGHT + 10:
                        p["alive"] = False; continue
                    if math.hypot(player.x - p["x"], player.y - p["y"]) < 18:
                        player.take_damage(1)
                        p["alive"] = False
                if all_dead:
                    self.timer = 0

            elif self.pattern == "warp_strike":
                all_dead = not self.data["projs"] or all(not p["alive"] for p in self.data["projs"])
                for p in self.data["projs"]:
                    if not p["alive"]:
                        continue
                    p["x"] += p["vx"]; p["y"] += p["vy"]
                    if p["x"] < -10 or p["x"] > WIDTH + 10 or p["y"] < -10 or p["y"] > HEIGHT + 10:
                        p["alive"] = False; continue
                    if math.hypot(player.x - p["x"], player.y - p["y"]) < 18:
                        player.take_damage(1)
                        p["alive"] = False
                if self.data["warps_left"] > 0:
                    self.data["warp_cooldown"] -= 1
                    if self.data["warp_cooldown"] <= 0 and all_dead:
                        corners = [(60.0, 60.0), (float(WIDTH - 60), 60.0),
                                   (60.0, float(HEIGHT - 60)), (float(WIDTH - 60), float(HEIGHT - 60))]
                        cx3, cy3 = random.choice(corners)
                        self.x, self.y = cx3, cy3
                        ddx3, ddy3 = player.x - self.x, player.y - self.y
                        d3 = math.hypot(ddx3, ddy3) or 1
                        ba3 = math.atan2(ddy3, ddx3)
                        self.data["projs"].extend([
                            {"x": float(self.x), "y": float(self.y),
                             "vx": math.cos(ba3 + (i - 1) * 0.3) * 9.0,
                             "vy": math.sin(ba3 + (i - 1) * 0.3) * 9.0,
                             "alive": True}
                            for i in range(3)
                        ])
                        self.data["warps_left"] -= 1
                        self.data["warp_cooldown"] = 55

            if self.timer <= 0:
                self.state = "vulnerable"
                self.timer = 120  # 2초 공격 기회
                self.data = {}

        elif self.state == "vulnerable":
            self.timer -= 1
            if self.timer <= 0:
                self.state = "idle"
                self.timer = 28 if self.enraged else 42

    def take_damage(self, amount):
        if self.is_vulnerable():
            self.hp -= amount
            if not self.enraged and self.hp <= self.max_hp // 2:
                self.enraged = True

    def draw(self, small_font):
        # 분열/거대화 상태에서는 본체를 다르게 그림
        if self.pattern == "split_squares" and self.state == "active":
            s = max(8, self.size // 3)
            col = (255, 50, 0) if self.enraged else ORANGE
            pygame.draw.rect(screen, col, pygame.Rect(int(self.x) - s // 2, int(self.y) - s // 2, s, s))
        elif self.pattern == "giant_slam" and self.state in ("telegraph", "active"):
            pass  # giant_slam body drawn below at grow_size
        else:
            if self.is_vulnerable():
                col = WHITE
            elif self.enraged:
                col = (255, 50, 0)
            else:
                col = ORANGE
            pygame.draw.rect(screen, col, self.get_rect())
            cx, cy, h = int(self.x), int(self.y), self.size // 2
            pygame.draw.line(screen, BLACK, (cx - h, cy), (cx + h, cy), 2)
            pygame.draw.line(screen, BLACK, (cx, cy - h), (cx, cy + h), 2)

        # 미러 대쉬 잔상
        if self.pattern == "mirror_dash" and self.data.get("counter_dashing"):
            ddx, ddy = self.data["dash_dir"]
            for i in range(1, 4):
                tx = int(self.x - ddx * i * 14)
                ty = int(self.y - ddy * i * 14)
                pygame.draw.rect(screen, ORANGE,
                                 pygame.Rect(tx - self.size // 2, ty - self.size // 2, self.size, self.size),
                                 max(1, 3 - i))

        # 점프 스탬프 충격파
        if self.pattern == "jump_stamp" and self.data.get("phase") == "shockwave":
            shock_y = int(self.data["target_y"])
            t_r = self.data.get("shockwave_timer", 0) / 38
            w = int((1 - t_r) * WIDTH + 80)
            pygame.draw.rect(screen, ORANGE,
                             pygame.Rect(max(0, WIDTH // 2 - w // 2), shock_y - 19, min(WIDTH, w), 38))

        # 잔상 대쉬 흔적
        if self.pattern == "phantom_trail" and self.state == "active":
            for tr in self.data.get("trails", []):
                if tr["exploded"]:
                    r = int(tr["radius"])
                    if r > 0:
                        pygame.draw.circle(screen, ORANGE, (int(tr["x"]), int(tr["y"])), r, 5)
                else:
                    pulse = max(5, int(20 * tr["fuse"] / 60))
                    pygame.draw.circle(screen, (255, 140, 0), (int(tr["x"]), int(tr["y"])), pulse, 3)

        # 분열 미니 사각형
        if self.pattern == "split_squares" and self.state == "active":
            for mini in self.data.get("minis", []):
                if mini["alive"]:
                    pygame.draw.rect(screen, ORANGE,
                                     pygame.Rect(int(mini["x"]) - 6, int(mini["y"]) - 6, 13, 13))

        # 오버드라이브 잔상
        if self.pattern == "orange_overdrive" and self.data.get("ghost_pos"):
            gx, gy = self.data["ghost_pos"]
            ghost_surf = pygame.Surface((26, 26), pygame.SRCALPHA)
            ghost_surf.fill((255, 80, 0, 130))
            screen.blit(ghost_surf, (int(gx) - 13, int(gy) - 13))

        # === NEW ORANGE MIRROR PATTERN DRAWS ===
        if self.pattern == "trail_bomb" and self.state == "active":
            for b in self.data.get("bombs", []):
                if b["exploded"]:
                    r = int(b["radius"])
                    if r > 0:
                        pygame.draw.circle(screen, ORANGE, (int(b["x"]), int(b["y"])), r, 4)
                else:
                    pulse = max(6, int(18 * b["fuse"] / 45))
                    pygame.draw.circle(screen, (255, 140, 0), (int(b["x"]), int(b["y"])), pulse, 3)

        if self.pattern == "quad_rush" and self.state in ("telegraph", "active"):
            for r in self.data.get("rushers", []):
                if r.get("alive", True):
                    pygame.draw.rect(screen, ORANGE,
                                     pygame.Rect(int(r["x"]) - 13, int(r["y"]) - 13, 26, 26))
                    pygame.draw.rect(screen, WHITE,
                                     pygame.Rect(int(r["x"]) - 13, int(r["y"]) - 13, 26, 26), 2)

        if self.pattern == "shadow_mimic" and self.state == "active":
            gx2 = self.data.get("ghost_x")
            gy2 = self.data.get("ghost_y")
            if gx2 is not None and gy2 is not None:
                ghost_surf2 = pygame.Surface((26, 26), pygame.SRCALPHA)
                ghost_surf2.fill((255, 80, 0, 140))
                screen.blit(ghost_surf2, (int(gx2) - 13, int(gy2) - 13))

        if self.pattern == "absorb_shield" and self.state in ("telegraph", "active"):
            sh = self.size + 18
            shield_surf = pygame.Surface((sh, sh), pygame.SRCALPHA)
            shield_surf.fill((255, 120, 0, 80))
            pygame.draw.rect(shield_surf, (255, 200, 0, 200), pygame.Rect(0, 0, sh, sh), 3)
            screen.blit(shield_surf, (int(self.x) - sh // 2, int(self.y) - sh // 2))

        if self.pattern == "screen_divide" and self.state in ("telegraph", "active"):
            hy = HEIGHT // 2
            danger = self.data.get("danger_top", True)
            overlay = pygame.Surface((WIDTH, HEIGHT // 2), pygame.SRCALPHA)
            alpha = 100 if self.state == "active" else 50
            overlay.fill((255, 100, 0, alpha))
            screen.blit(overlay, (0, 0 if danger else hy))
            dcol = (255, 120, 0) if self.state == "active" else (150, 70, 0)
            pygame.draw.line(screen, dcol, (0, hy), (WIDTH, hy), 3)

        if self.pattern == "giant_slam" and self.state in ("telegraph", "active"):
            gs = int(self.data.get("grow_size", self.size))
            gcol = (255, 50, 0) if self.enraged else (255, 90, 0)
            pygame.draw.rect(screen, gcol,
                             pygame.Rect(int(self.x) - gs // 2, int(self.y) - gs // 2, gs, gs))
            pygame.draw.rect(screen, WHITE,
                             pygame.Rect(int(self.x) - gs // 2, int(self.y) - gs // 2, gs, gs), 3)

        if self.pattern in ("fake_charge", "burst_spread", "warp_strike") and self.state == "active":
            for p in self.data.get("projs", []):
                if p.get("alive", False):
                    pygame.draw.circle(screen, ORANGE, (int(p["x"]), int(p["y"])), 13)
                    pygame.draw.circle(screen, WHITE, (int(p["x"]), int(p["y"])), 5)

        bar_w = 220
        pygame.draw.rect(screen, (60, 60, 60), (WIDTH // 2 - bar_w // 2, 16, bar_w, 16))
        bar_col = (255, 50, 0) if self.enraged else ORANGE
        pygame.draw.rect(screen, bar_col,
                         (WIDTH // 2 - bar_w // 2, 16,
                          int(bar_w * max(self.hp, 0) / self.max_hp), 16))
        label = self.name + (" [OVERDRIVE]" if self.enraged else "")
        name_text = small_font.render(label, True, bar_col)
        screen.blit(name_text, (WIDTH // 2 - name_text.get_width() // 2, 34))


# ═══════════════════════════════════════════════════════════════════
#  PAPYRUS BOSS
# ═══════════════════════════════════════════════════════════════════
class PapyrusBoss:
    name = "PAPYRUS"
    TURN_SEQ = [
        "basic_bones", "blue_soul", "blue_bones_mix",
        "cool_dude", "variable_height", "moving_barriers",
        "bone_platforms", "annoying_dog", "cool_dude",
        "combo_attack",
    ]
    LOOP_SEQ = [
        "basic_bones", "moving_barriers", "cool_dude",
        "blue_bones_mix", "variable_height", "combo_attack",
        "bone_platforms", "blue_soul", "cool_dude",
    ]
    PATTERN_QUOTE = {
        "basic_bones":    "* FIRST! THE BASIC ATTACK!",
        "blue_soul":      "* YOUR SOUL IS NOW BLUE!",
        "blue_bones_mix": "* CAN YOU TELL THE DIFFERENCE?!",
        "variable_height":"* BONES OF VARYING HEIGHTS!",
        "moving_barriers":"* THIS REQUIRES PRECISION!",
        "bone_platforms": "* WATCH YOUR STEP, HUMAN!",
        "annoying_dog":   "* NOW FOR MY SPECIAL ATTACK!",
        "cool_dude":      "* THIS IS... COOL DUDE!",
        "combo_attack":   "* NYEH HEH HEH! ALL AT ONCE!",
    }

    def __init__(self):
        self.x = float(WIDTH * 0.74)
        self.y = float(HEIGHT // 2)
        self.size = 90
        self.hp = 80
        self.max_hp = 80
        self.state = "idle"
        self.timer = 40
        self.pattern = None
        self.data = {}
        self.turn = 0
        self.hit_particles = []
        self.quote_timer = 0

    def get_rect(self):
        return pygame.Rect(int(self.x) - self.size // 2,
                           int(self.y) - self.size // 2,
                           self.size, self.size)

    def is_vulnerable(self):
        return self.state == "vulnerable"

    def start_pattern(self):
        if self.turn < len(self.TURN_SEQ):
            self.pattern = self.TURN_SEQ[self.turn]
        else:
            choices = [p for p in self.LOOP_SEQ if p != self.pattern] or self.LOOP_SEQ
            self.pattern = random.choice(choices)
        self.turn += 1
        self.state = "telegraph"
        self.data = {}
        self.quote_timer = 80

        tele = {"basic_bones": 25, "blue_soul": 30, "blue_bones_mix": 30,
                "variable_height": 25, "moving_barriers": 30,
                "bone_platforms": 28, "annoying_dog": 20, "cool_dude": 28,
                "combo_attack": 35}
        act = {"basic_bones": 220, "blue_soul": 250, "blue_bones_mix": 230,
               "variable_height": 210, "moving_barriers": 240,
               "bone_platforms": 220, "annoying_dog": 140, "cool_dude": 200,
               "combo_attack": 300}
        self.timer = tele.get(self.pattern, 25)
        self.data["_act"] = act.get(self.pattern, 200)

        if self.pattern in ("basic_bones", "blue_soul", "blue_bones_mix",
                             "variable_height"):
            self.data.update({"bones": [], "spawn_timer": 0, "spawn_count": 0})
        elif self.pattern == "moving_barriers":
            self.data["barriers"] = [
                {"x": float(WIDTH + 80 + i * 160),
                 "gap_y": float(random.randint(80, HEIGHT - 80)),
                 "gap_h": 90, "vy": random.choice([-1.2, 1.2]), "alive": True}
                for i in range(5)
            ]
        elif self.pattern == "bone_platforms":
            self.data["platforms"] = []
            self.data["spawn_timer"] = 0
            self.data["spawned"] = 0
        elif self.pattern == "annoying_dog":
            self.data["dog_x"] = float(-60)
            self.data["dog_phase"] = "enter"
            self.data["dog_timer"] = 0
            self.data["bone_x"] = float(WIDTH + 200)
            self.data["show_bone"] = False
        elif self.pattern == "cool_dude":
            self.data["bone_x"] = float(WIDTH + 20)
            gap = random.randint(int(HEIGHT * 0.2), int(HEIGHT * 0.6))
            self.data["gap_y"] = float(gap)
            self.data["gap_h"] = 70
            self.data["bone_h"] = HEIGHT
        elif self.pattern == "combo_attack":
            self.data["bones"] = []
            self.data["spawn_timer"] = 0
            self.data["spawn_count"] = 0
            self.data["barriers"] = [
                {"x": float(WIDTH + 80 + i * 200),
                 "gap_y": float(random.randint(80, HEIGHT - 80)),
                 "gap_h": 80, "vy": random.choice([-1.0, 1.0]), "alive": True}
                for i in range(3)
            ]
            gap2 = random.randint(int(HEIGHT * 0.2), int(HEIGHT * 0.6))
            self.data["cool_x"] = float(WIDTH + 20)
            self.data["cool_gap_y"] = float(gap2)
            self.data["cool_gap_h"] = 60

    def update(self, player):
        tx, ty = float(WIDTH * 0.74), float(HEIGHT // 2)
        self.x += (tx - self.x) * 0.018
        self.y += (ty - self.y) * 0.018

        if self.quote_timer > 0:
            self.quote_timer -= 1

        if self.state == "idle":
            self.timer -= 1
            if self.timer <= 0:
                self.start_pattern()

        elif self.state == "telegraph":
            self.timer -= 1
            if self.timer <= 0:
                self.state = "active"
                self.timer = self.data.pop("_act", 200)

        elif self.state == "active":
            self.timer -= 1
            p = self.pattern
            if p == "basic_bones":        self._do_basic_bones(player, blue=False, mixed=False)
            elif p == "blue_soul":         self._do_basic_bones(player, blue=False, mixed=False, soul=True)
            elif p == "blue_bones_mix":    self._do_basic_bones(player, blue=True,  mixed=True)
            elif p == "variable_height":   self._do_variable_height(player)
            elif p == "moving_barriers":   self._do_moving_barriers(player)
            elif p == "bone_platforms":    self._do_bone_platforms(player)
            elif p == "annoying_dog":      self._do_annoying_dog()
            elif p == "cool_dude":         self._do_cool_dude(player)
            elif p == "combo_attack":      self._do_combo_attack(player)

            if self.timer <= 0:
                self.state = "vulnerable"
                self.timer = 90
                self.data = {}

        elif self.state == "vulnerable":
            self.timer -= 1
            if self.timer <= 0:
                self.state = "idle"
                self.timer = 22

        for pt in self.hit_particles:
            pt["x"] += pt["vx"]; pt["y"] += pt["vy"]; pt["life"] -= 1
        self.hit_particles = [pt for pt in self.hit_particles if pt["life"] > 0]

    # ── helpers ──

    def _spawn_bone(self, y, h, speed=None, blue=False):
        spd = speed if speed is not None else random.uniform(4.0, 5.5)
        return {"x": float(WIDTH + 10), "y": float(y), "h": h, "w": 900,
                "speed": spd, "blue": blue, "alive": True}

    def _move_bones(self, player, prev_px, prev_py):
        moving = abs(player.x - prev_px) > 0.5 or abs(player.y - prev_py) > 0.5
        for b in self.data["bones"]:
            if not b["alive"]: continue
            b["x"] -= b["speed"]
            br = pygame.Rect(int(b["x"]), int(b["y"]) - b["h"] // 2, int(b["w"]), b["h"])
            if br.colliderect(player.get_rect()):
                if not b["blue"] or moving:
                    player.take_damage(1)
            if b["x"] + b["w"] < -20:
                b["alive"] = False
        self.data["bones"] = [b for b in self.data["bones"] if b["alive"]]

    def _do_basic_bones(self, player, blue=False, mixed=False, soul=False):
        d = self.data
        if "prev_px" not in d:
            d["prev_px"], d["prev_py"] = player.x, player.y
        prev_px, prev_py = d["prev_px"], d["prev_py"]
        d["prev_px"], d["prev_py"] = player.x, player.y

        max_c = 10; interval = 32; bh = 18
        d["spawn_timer"] -= 1
        if d["spawn_timer"] <= 0 and d["spawn_count"] < max_c:
            yp = random.randint(60, HEIGHT - 60)
            is_blue = mixed and random.random() < 0.45
            d["bones"].append(self._spawn_bone(yp, bh, blue=is_blue))
            d["spawn_count"] += 1
            d["spawn_timer"] = interval

        self._move_bones(player, prev_px, prev_py)
        if d["spawn_count"] >= max_c and not d["bones"]:
            self.timer = 0

    def _do_variable_height(self, player):
        d = self.data
        if "prev_px" not in d:
            d["prev_px"], d["prev_py"] = player.x, player.y
        prev_px, prev_py = d["prev_px"], d["prev_py"]
        d["prev_px"], d["prev_py"] = player.x, player.y

        max_c = 10; interval = 38
        d["spawn_timer"] -= 1
        if d["spawn_timer"] <= 0 and d["spawn_count"] < max_c:
            tall = (d["spawn_count"] % 3 == 2)
            if tall:
                bh = HEIGHT - 60
                yp = HEIGHT // 2
            else:
                bh = random.randint(16, 28)
                yp = random.randint(70, HEIGHT - 70)
            d["bones"].append(self._spawn_bone(yp, bh))
            d["spawn_count"] += 1
            d["spawn_timer"] = interval

        self._move_bones(player, prev_px, prev_py)
        if d["spawn_count"] >= max_c and not d["bones"]:
            self.timer = 0

    def _do_moving_barriers(self, player):
        d = self.data
        spd = 3.0
        for b in d["barriers"]:
            if not b["alive"]: continue
            b["x"] -= spd
            b["gap_y"] += b["vy"]
            if b["gap_y"] < 60 or b["gap_y"] > HEIGHT - 60:
                b["vy"] *= -1
            gap_y, gap_h = int(b["gap_y"]), b["gap_h"]
            bx = int(b["x"])
            top_rect = pygame.Rect(bx - 10, 0, 20, max(0, gap_y - gap_h // 2))
            bot_rect = pygame.Rect(bx - 10, gap_y + gap_h // 2, 20,
                                   max(0, HEIGHT - gap_y - gap_h // 2))
            if (top_rect.colliderect(player.get_rect()) or
                    bot_rect.colliderect(player.get_rect())):
                player.take_damage(1)
            if b["x"] < -30:
                b["alive"] = False
        d["barriers"] = [b for b in d["barriers"] if b["alive"]]
        if not d["barriers"]:
            self.timer = 0

    def _do_bone_platforms(self, player):
        d = self.data
        FLOOR_Y = HEIGHT * 0.72
        d["spawn_timer"] -= 1
        if d["spawn_timer"] <= 0 and d["spawned"] < 14:
            yp = random.randint(int(HEIGHT * 0.30), int(HEIGHT * 0.65))
            d["platforms"].append({"x": float(WIDTH + 20), "y": float(yp),
                                   "w": 80, "h": 12, "speed": random.uniform(3.0, 4.5)})
            d["spawned"] += 1
            d["spawn_timer"] = 22

        for pl in d["platforms"]:
            pl["x"] -= pl["speed"]
        d["platforms"] = [pl for pl in d["platforms"] if pl["x"] + pl["w"] > -20]

        on_platform = any(
            pygame.Rect(int(pl["x"]) - pl["w"] // 2, int(pl["y"]) - pl["h"] // 2,
                        pl["w"], pl["h"]).colliderect(player.get_rect())
            for pl in d["platforms"]
        )
        if player.y > FLOOR_Y and not on_platform and not player.dashing:
            player.take_damage(1)

        if d["spawned"] >= 14 and not d["platforms"]:
            self.timer = 0

    def _do_annoying_dog(self):
        d = self.data
        d["dog_timer"] += 1
        phase = d["dog_phase"]
        if phase == "enter":
            d["dog_x"] += 6.0
            if d["dog_x"] > WIDTH // 3:
                d["dog_phase"] = "wait"; d["dog_timer"] = 0
        elif phase == "wait":
            if d["dog_timer"] > 35:
                d["show_bone"] = True
                d["dog_phase"] = "steal"
                d["dog_timer"] = 0
        elif phase == "steal":
            d["dog_x"] += 9.0
            if d["dog_x"] > WIDTH + 80:
                d["dog_phase"] = "done"
        elif phase == "done":
            if d["dog_timer"] > 30:
                self.timer = 0

    def _do_cool_dude(self, player):
        d = self.data
        d["bone_x"] -= 1.8
        bx = int(d["bone_x"]); gap_y = int(d["gap_y"]); gap_h = int(d["gap_h"])
        top_r = pygame.Rect(bx - 14, 0, 28, max(0, gap_y - gap_h // 2))
        bot_r = pygame.Rect(bx - 14, gap_y + gap_h // 2, 28,
                            max(0, HEIGHT - gap_y - gap_h // 2))
        if top_r.colliderect(player.get_rect()) or bot_r.colliderect(player.get_rect()):
            player.take_damage(2)
        if d["bone_x"] < -30:
            self.timer = 0

    def _do_combo_attack(self, player):
        d = self.data

        # White bones from right
        max_c = 8; interval = 40; bh = 20
        d["spawn_timer"] -= 1
        if d["spawn_timer"] <= 0 and d["spawn_count"] < max_c:
            yp = random.randint(60, HEIGHT - 60)
            d["bones"].append(self._spawn_bone(yp, bh, speed=4.5))
            d["spawn_count"] += 1
            d["spawn_timer"] = interval

        for b in d["bones"]:
            if not b["alive"]: continue
            b["x"] -= b["speed"]
            br = pygame.Rect(int(b["x"]), int(b["y"]) - b["h"] // 2, int(b["w"]), b["h"])
            if br.colliderect(player.get_rect()):
                player.take_damage(1)
            if b["x"] + b["w"] < -20:
                b["alive"] = False
        d["bones"] = [b for b in d["bones"] if b["alive"]]

        # Moving barriers (yellow tint to differentiate)
        for bar in d["barriers"]:
            if not bar["alive"]: continue
            bar["x"] -= 2.5
            bar["gap_y"] += bar["vy"]
            if bar["gap_y"] < 60 or bar["gap_y"] > HEIGHT - 60:
                bar["vy"] *= -1
            gap_y, gap_h = int(bar["gap_y"]), bar["gap_h"]
            bx = int(bar["x"])
            top_rect = pygame.Rect(bx - 10, 0, 20, max(0, gap_y - gap_h // 2))
            bot_rect = pygame.Rect(bx - 10, gap_y + gap_h // 2, 20,
                                   max(0, HEIGHT - gap_y - gap_h // 2))
            if (top_rect.colliderect(player.get_rect()) or
                    bot_rect.colliderect(player.get_rect())):
                player.take_damage(1)
            if bar["x"] < -30:
                bar["alive"] = False
        d["barriers"] = [bar for bar in d["barriers"] if bar["alive"]]

        # Cool dude wall (slower than solo)
        d["cool_x"] -= 1.2
        cx = int(d["cool_x"]); gap_y2 = int(d["cool_gap_y"]); gap_h2 = int(d["cool_gap_h"])
        top_r = pygame.Rect(cx - 14, 0, 28, max(0, gap_y2 - gap_h2 // 2))
        bot_r = pygame.Rect(cx - 14, gap_y2 + gap_h2 // 2, 28,
                            max(0, HEIGHT - gap_y2 - gap_h2 // 2))
        if top_r.colliderect(player.get_rect()) or bot_r.colliderect(player.get_rect()):
            player.take_damage(2)

        all_done = (d["spawn_count"] >= max_c and not d["bones"]
                    and not d["barriers"] and d["cool_x"] < -30)
        if all_done:
            self.timer = 0

    def take_damage(self, amount):
        if not self.is_vulnerable(): return
        self.hp -= amount
        for _ in range(8):
            a = random.uniform(0, 2 * math.pi)
            spd = random.uniform(2, 6)
            self.hit_particles.append({
                "x": float(self.x), "y": float(self.y),
                "vx": math.cos(a) * spd, "vy": math.sin(a) * spd,
                "life": random.randint(12, 22), "max_life": 22,
            })

    def _draw_bone(self, bx, by_center, bw, bh, col, border):
        cy = by_center
        shaft_h = max(4, bh - 8)
        pygame.draw.rect(screen, col,
                         pygame.Rect(int(bx), int(cy - shaft_h // 2), int(bw), shaft_h))
        kr = bh // 2 + 2
        lx = int(bx) + kr // 2
        pygame.draw.circle(screen, col, (lx, int(cy - bh // 4)), kr)
        pygame.draw.circle(screen, col, (lx, int(cy + bh // 4)), kr)
        rx = int(bx + bw) - kr // 2
        pygame.draw.circle(screen, col, (rx, int(cy - bh // 4)), kr)
        pygame.draw.circle(screen, col, (rx, int(cy + bh // 4)), kr)
        pygame.draw.rect(screen, border,
                         pygame.Rect(int(bx), int(cy - shaft_h // 2), int(bw), shaft_h), 2)

    def draw(self, small_font, blue_soul_mode=False):
        # Papyrus sprite
        sprite = pygame.transform.scale(PAPYRUS_IMAGE, (self.size, self.size))
        if self.is_vulnerable():
            tinted = sprite.copy()
            tinted.fill((255, 230, 80, 0), special_flags=pygame.BLEND_RGBA_ADD)
            sprite = tinted
        sx = int(self.x) - self.size // 2
        sy = int(self.y) - self.size // 2
        screen.blit(sprite, (sx, sy))

        # Pattern visuals
        p = self.pattern

        # Bones (basic / blue_soul / blue_bones_mix / variable_height)
        for b in self.data.get("bones", []):
            if not b.get("alive", True): continue
            col = (80, 130, 255) if b.get("blue") else WHITE
            border = (160, 200, 255) if b.get("blue") else (200, 200, 200)
            self._draw_bone(b["x"], b["y"], b["w"], b["h"], col, border)

        # Moving barriers
        for bar in self.data.get("barriers", []):
            if not bar.get("alive", True): continue
            bx = int(bar["x"]); gap_y = int(bar["gap_y"]); gap_h = bar["gap_h"]
            top_r = pygame.Rect(bx - 10, 0, 20, max(0, gap_y - gap_h // 2))
            bot_r = pygame.Rect(bx - 10, gap_y + gap_h // 2, 20,
                                max(0, HEIGHT - gap_y - gap_h // 2))
            pygame.draw.rect(screen, WHITE, top_r)
            pygame.draw.rect(screen, WHITE, bot_r)
            pygame.draw.rect(screen, (200, 200, 200), top_r, 2)
            pygame.draw.rect(screen, (200, 200, 200), bot_r, 2)
            # gap indicator
            pygame.draw.line(screen, (180, 255, 180),
                             (bx, gap_y - gap_h // 2), (bx, gap_y + gap_h // 2), 1)

        # Bone platforms
        if p == "bone_platforms":
            # Danger floor
            fl_surf = pygame.Surface((WIDTH, int(HEIGHT * 0.28) + 1), pygame.SRCALPHA)
            fl_surf.fill((255, 80, 80, 40))
            screen.blit(fl_surf, (0, int(HEIGHT * 0.72)))
            pygame.draw.line(screen, (255, 80, 80), (0, int(HEIGHT * 0.72)),
                             (WIDTH, int(HEIGHT * 0.72)), 2)
            # Platforms
            for pl in self.data.get("platforms", []):
                px2 = int(pl["x"]) - pl["w"] // 2
                py2 = int(pl["y"]) - pl["h"] // 2
                pygame.draw.rect(screen, WHITE, pygame.Rect(px2, py2, pl["w"], pl["h"]))
                pygame.draw.rect(screen, (180, 180, 180),
                                 pygame.Rect(px2, py2, pl["w"], pl["h"]), 2)

        # Annoying dog
        if p == "annoying_dog":
            d = self.data
            dog_x = int(d["dog_x"])
            # dog body
            pygame.draw.ellipse(screen, WHITE, (dog_x - 25, HEIGHT // 2 - 18, 50, 36))
            # ear
            pygame.draw.ellipse(screen, WHITE, (dog_x - 5, HEIGHT // 2 - 30, 18, 20))
            # eye
            pygame.draw.circle(screen, BLACK, (dog_x + 8, HEIGHT // 2 - 8), 4)
            # tail
            pygame.draw.arc(screen, WHITE,
                            (dog_x - 40, HEIGHT // 2 - 30, 24, 24),
                            0, math.pi, 4)
            if d.get("show_bone"):
                # giant bone being carried
                bx_d = dog_x + 30
                pygame.draw.line(screen, WHITE, (bx_d, HEIGHT // 2 - 5),
                                 (bx_d + 80, HEIGHT // 2 - 5), 14)
                pygame.draw.circle(screen, WHITE, (bx_d, HEIGHT // 2 - 5), 12)
                pygame.draw.circle(screen, WHITE, (bx_d + 80, HEIGHT // 2 - 5), 12)

        # Cool dude bone
        if p == "cool_dude" and self.state == "active":
            d = self.data
            bx_c = int(d["bone_x"]); gap_y = int(d["gap_y"]); gap_h = int(d["gap_h"])
            top_r2 = pygame.Rect(bx_c - 14, 0, 28, max(0, gap_y - gap_h // 2))
            bot_r2 = pygame.Rect(bx_c - 14, gap_y + gap_h // 2, 28,
                                 max(0, HEIGHT - gap_y - gap_h // 2))
            pygame.draw.rect(screen, WHITE, top_r2)
            pygame.draw.rect(screen, WHITE, bot_r2)
            pygame.draw.rect(screen, (200, 200, 200), top_r2, 3)
            pygame.draw.rect(screen, (200, 200, 200), bot_r2, 3)
            # "COOL DUDE" text
            cd_t = small_font.render("COOL DUDE", True, (255, 140, 0))
            if top_r2.height > 30:
                screen.blit(cd_t, (bx_c - cd_t.get_width() // 2, top_r2.height // 2 - 10))
            if bot_r2.height > 30:
                screen.blit(cd_t, (bx_c - cd_t.get_width() // 2,
                                   gap_y + gap_h // 2 + bot_r2.height // 2 - 10))

        # Combo attack visuals
        if p == "combo_attack" and self.state == "active":
            cd = self.data
            for b in cd.get("bones", []):
                if not b.get("alive", True): continue
                self._draw_bone(b["x"], b["y"], b["w"], b["h"], WHITE, (200, 200, 200))
            for bar in cd.get("barriers", []):
                if not bar.get("alive", True): continue
                bx2 = int(bar["x"]); gy2 = int(bar["gap_y"]); gh2 = bar["gap_h"]
                top_rb = pygame.Rect(bx2 - 10, 0, 20, max(0, gy2 - gh2 // 2))
                bot_rb = pygame.Rect(bx2 - 10, gy2 + gh2 // 2, 20,
                                     max(0, HEIGHT - gy2 - gh2 // 2))
                pygame.draw.rect(screen, (220, 220, 100), top_rb)
                pygame.draw.rect(screen, (220, 220, 100), bot_rb)
                pygame.draw.rect(screen, (255, 255, 180), top_rb, 2)
                pygame.draw.rect(screen, (255, 255, 180), bot_rb, 2)
            cx_c = int(cd.get("cool_x", WIDTH + 20))
            gyc = int(cd.get("cool_gap_y", HEIGHT // 2))
            ghc = int(cd.get("cool_gap_h", 60))
            top_rc = pygame.Rect(cx_c - 14, 0, 28, max(0, gyc - ghc // 2))
            bot_rc = pygame.Rect(cx_c - 14, gyc + ghc // 2, 28,
                                 max(0, HEIGHT - gyc - ghc // 2))
            pygame.draw.rect(screen, (255, 140, 0), top_rc)
            pygame.draw.rect(screen, (255, 140, 0), bot_rc)
            pygame.draw.rect(screen, (255, 200, 80), top_rc, 3)
            pygame.draw.rect(screen, (255, 200, 80), bot_rc, 3)
            cd_t2 = small_font.render("COOL DUDE", True, WHITE)
            if top_rc.height > 30:
                screen.blit(cd_t2, (cx_c - cd_t2.get_width() // 2, top_rc.height // 2 - 10))
            if bot_rc.height > 30:
                screen.blit(cd_t2, (cx_c - cd_t2.get_width() // 2,
                                    gyc + ghc // 2 + bot_rc.height // 2 - 10))

        # Blue soul mode indicator
        if blue_soul_mode:
            bs_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            bs_surf.fill((0, 0, 180, 18))
            screen.blit(bs_surf, (0, 0))
            bs_t = small_font.render("BLUE SOUL MODE", True, (80, 130, 255))
            screen.blit(bs_t, (12, 14))

        # Mid-turn quote
        if self.quote_timer > 0 and self.pattern:
            q = self.PATTERN_QUOTE.get(self.pattern, "")
            if q:
                q_surf = small_font.render(q, True, (255, 220, 100))
                alpha = min(255, self.quote_timer * 3)
                q_surf.set_alpha(alpha)
                screen.blit(q_surf, (WIDTH // 2 - q_surf.get_width() // 2, HEIGHT - 55))

        # HP bar
        bar_w = 200
        pygame.draw.rect(screen, (60, 60, 60), (WIDTH // 2 - bar_w // 2, 16, bar_w, 16))
        pygame.draw.rect(screen, (255, 120, 60),
                         (WIDTH // 2 - bar_w // 2, 16,
                          int(bar_w * max(self.hp, 0) / self.max_hp), 16))
        nt = small_font.render(self.name, True, WHITE)
        screen.blit(nt, (WIDTH // 2 - nt.get_width() // 2, 34))

        # Hit particles
        for pt in self.hit_particles:
            ratio = pt["life"] / pt["max_life"]
            pygame.draw.circle(screen, (int(255 * ratio), int(140 * ratio), int(60 * ratio)),
                               (int(pt["x"]), int(pt["y"])), max(1, int(5 * ratio)))




# ═══════════════════════════════════════════════════════════════════
#  TORIEL BOSS
# ═══════════════════════════════════════════════════════════════════
class TorielBoss:
    """토리엘 보스. 화염 공격 + 자비 시스템 (HP<=1 화염 회피)."""
    name = "TORIEL"

    TURN_SEQ = [
        "hand_flame",        # 1  두 손의 화염구
        "fire_waves",        # 2  수평 파도
        "targeting_flames",  # 3  추적 화염
        "crossfire_burst",   # 4  십자 폭발
        "blazing_flower",    # 5  꽃잎 방사
        "swiping_flames",    # 6  수평 스와이프
        "warm_embrace",      # 7  포위 화염
        "hesitant_flame",    # 8  망설이는 불꽃
        "crossfire_hands",   # 9  교차 화염
        "tracing_fire",      # 10 흔적 추적 불
        "mercy_pattern",     # 11 자비 패턴
    ]
    LOOP_SEQ = [
        "hand_flame", "crossfire_burst", "targeting_flames",
        "fire_waves", "blazing_flower", "swiping_flames",
        "warm_embrace", "hesitant_flame", "crossfire_hands",
        "tracing_fire",
    ]
    PATTERN_QUOTE = {
        "hand_flame":       "* My child... let me show you my power.",
        "fire_waves":       "* Waves of fire, like a warm hearth.",
        "targeting_flames": "* I can always find you, my child.",
        "crossfire_burst":  "* Please, stop this fight.",
        "blazing_flower":   "* Even in battle, I see beauty.",
        "swiping_flames":   "* You must be exhausted. Turn back.",
        "warm_embrace":     "* Come, let me hold you close.",
        "hesitant_flame":   "* ...Do I really have to do this?",
        "crossfire_hands":  "* Both hands together... forgive me.",
        "tracing_fire":     "* I will always follow you, my child.",
        "mercy_pattern":    "* I do not wish to hurt you.",
    }

    def __init__(self):
        self.x = float(WIDTH * 0.74)
        self.y = float(HEIGHT // 2)
        self.size = 90
        self.hp = 100
        self.max_hp = 100
        self.state = "idle"
        self.timer = 40
        self.pattern = None
        self.data = {}
        self.turn = 0
        self.hit_particles = []
        self.quote_timer = 0

    def get_rect(self):
        return pygame.Rect(int(self.x) - self.size // 2,
                           int(self.y) - self.size // 2,
                           self.size, self.size)

    def is_vulnerable(self):
        return self.state == "vulnerable"

    def start_pattern(self):
        if self.turn < len(self.TURN_SEQ):
            self.pattern = self.TURN_SEQ[self.turn]
        else:
            self.pattern = self.LOOP_SEQ[(self.turn - len(self.TURN_SEQ)) % len(self.LOOP_SEQ)]
        self.turn += 1
        self.state = "telegraph"
        self.data = {}
        self.quote_timer = 80

        tele = {
            "hand_flame": 30, "fire_waves": 30, "targeting_flames": 28,
            "crossfire_burst": 25, "blazing_flower": 30, "swiping_flames": 25,
            "warm_embrace": 30, "hesitant_flame": 35, "crossfire_hands": 28,
            "tracing_fire": 25, "mercy_pattern": 20,
        }
        act = {
            "hand_flame": 240, "fire_waves": 280, "targeting_flames": 260,
            "crossfire_burst": 220, "blazing_flower": 260, "swiping_flames": 240,
            "warm_embrace": 240, "hesitant_flame": 200, "crossfire_hands": 280,
            "tracing_fire": 260, "mercy_pattern": 180,
        }
        self.timer = tele.get(self.pattern, 28)
        self.data["_act"] = act.get(self.pattern, 220)

        if self.pattern == "hand_flame":
            self.data["big_flames"] = []
            self.data["flames"] = []
            self.data["spawn_timer"] = 0
            self.data["spawn_count"] = 0
        elif self.pattern == "fire_waves":
            self.data["flames"] = []
            self.data["spawn_timer"] = 0
            self.data["wave_count"] = 0
        elif self.pattern == "targeting_flames":
            self.data["flames"] = []
            self.data["spawn_timer"] = 0
            self.data["spawn_count"] = 0
        elif self.pattern == "crossfire_burst":
            self.data["flames"] = []
            self.data["burst_timer"] = 0
            self.data["burst_count"] = 0
        elif self.pattern == "blazing_flower":
            self.data["flames"] = []
            self.data["angle"] = 0.0
            self.data["spawn_timer"] = 0
            self.data["rings"] = 0
        elif self.pattern == "swiping_flames":
            self.data["flames"] = []
            self.data["spawn_timer"] = 0
            self.data["sweep_count"] = 0
        elif self.pattern == "warm_embrace":
            self.data["flames"] = []
            self.data["spawned"] = False
        elif self.pattern == "hesitant_flame":
            self.data["flames"] = []
        elif self.pattern == "crossfire_hands":
            self.data["flames"] = []
            self.data["spawn_timer"] = 0
        elif self.pattern == "tracing_fire":
            self.data["flames"] = []
            self.data["trail"] = []
            self.data["spawn_timer"] = 0
        elif self.pattern == "mercy_pattern":
            self.data["flames"] = []
            self.data["spawn_timer"] = 0

    def _flame(self, x, y, vx, vy, r=10):
        return {"x": float(x), "y": float(y), "vx": float(vx), "vy": float(vy),
                "r": r, "alive": True}

    def _move_flames(self, player, mercy=False):
        for f in self.data.get("flames", []):
            if not f["alive"]:
                continue
            if mercy and player.hp <= 1:
                dx = player.x - f["x"]; dy = player.y - f["y"]
                dist = math.hypot(dx, dy)
                if dist > 1:
                    perp_x = -dy / dist; perp_y = dx / dist
                    repel = max(0.0, 1.0 - dist / 350.0) * 3.0
                    f["vx"] += (-dx / dist * repel + perp_x * 1.0)
                    f["vy"] += (-dy / dist * repel + perp_y * 1.0)
                    spd = math.hypot(f["vx"], f["vy"])
                    if spd > 5.0:
                        f["vx"] = f["vx"] / spd * 5.0
                        f["vy"] = f["vy"] / spd * 5.0
            f["x"] += f["vx"]
            f["y"] += f["vy"]
            if f["x"] < -80 or f["x"] > WIDTH + 80 or f["y"] < -80 or f["y"] > HEIGHT + 80:
                f["alive"] = False
            if f["alive"] and player.hit_cooldown <= 0:
                if math.hypot(f["x"] - player.x, f["y"] - player.y) < f["r"] + player.size * 0.45:
                    player.take_damage(1)
        self.data["flames"] = [f for f in self.data.get("flames", []) if f["alive"]]

    def update(self, player):
        tx, ty = float(WIDTH * 0.74), float(HEIGHT // 2)
        self.x += (tx - self.x) * 0.018
        self.y += (ty - self.y) * 0.018

        if self.quote_timer > 0:
            self.quote_timer -= 1

        if self.state == "idle":
            self.timer -= 1
            if self.timer <= 0:
                self.start_pattern()

        elif self.state == "telegraph":
            self.timer -= 1
            if self.timer <= 0:
                self.state = "active"
                self.timer = self.data.pop("_act", 220)

        elif self.state == "active":
            self.timer -= 1
            p = self.pattern
            if   p == "hand_flame":        self._do_hand_flame(player)
            elif p == "fire_waves":        self._do_fire_waves(player)
            elif p == "targeting_flames":  self._do_targeting_flames(player)
            elif p == "crossfire_burst":   self._do_crossfire_burst(player)
            elif p == "blazing_flower":    self._do_blazing_flower(player)
            elif p == "swiping_flames":    self._do_swiping_flames(player)
            elif p == "warm_embrace":      self._do_warm_embrace(player)
            elif p == "hesitant_flame":    self._do_hesitant_flame(player)
            elif p == "crossfire_hands":   self._do_crossfire_hands(player)
            elif p == "tracing_fire":      self._do_tracing_fire(player)
            elif p == "mercy_pattern":     self._do_mercy_pattern(player)

            if self.timer <= 0:
                self.state = "vulnerable"
                self.timer = 150
                self.data = {}

        elif self.state == "vulnerable":
            self.timer -= 1
            if self.timer <= 0:
                self.state = "idle"
                self.timer = 22

        for pt in self.hit_particles:
            pt["x"] += pt["vx"]; pt["y"] += pt["vy"]; pt["life"] -= 1
        self.hit_particles = [pt for pt in self.hit_particles if pt["life"] > 0]

    # ─── Pattern Implementations ───────────────────────────────────

    def _do_hand_flame(self, player):
        d = self.data
        d["spawn_timer"] = d.get("spawn_timer", 0) + 1
        if d["spawn_timer"] % 55 == 1 and d["spawn_count"] < 4:
            d["spawn_count"] += 1
            tx = player.x + random.uniform(-30, 30)
            ty = player.y + random.uniform(-30, 30)
            ly = float(HEIGHT // 2 + random.randint(-100, 100))
            ry = float(HEIGHT // 2 + random.randint(-100, 100))
            d["big_flames"].append(
                {"x": float(-40), "y": ly, "tx": tx, "ty": ty,
                 "r": 20, "speed": 3.8, "alive": True, "split": False})
            d["big_flames"].append(
                {"x": float(WIDTH + 40), "y": ry, "tx": tx, "ty": ty,
                 "r": 20, "speed": 3.8, "alive": True, "split": False})

        for bf in d["big_flames"]:
            if not bf["alive"]: continue
            ddx = bf["tx"] - bf["x"]; ddy = bf["ty"] - bf["y"]
            dist = math.hypot(ddx, ddy)
            if dist < 18 and not bf["split"]:
                bf["split"] = True; bf["alive"] = False
                for k in range(8):
                    angle = k * (math.pi / 4) + random.uniform(-0.15, 0.15)
                    spd = random.uniform(3.0, 5.0)
                    d["flames"].append(
                        self._flame(bf["tx"], bf["ty"],
                                    math.cos(angle) * spd, math.sin(angle) * spd, r=11))
            elif dist > 0 and not bf["split"]:
                bf["x"] += ddx / dist * bf["speed"]
                bf["y"] += ddy / dist * bf["speed"]
            if bf["alive"] and player.hit_cooldown <= 0:
                if math.hypot(bf["x"] - player.x, bf["y"] - player.y) < bf["r"] + player.size * 0.45:
                    player.take_damage(1)
        d["big_flames"] = [bf for bf in d["big_flames"] if bf["alive"]]
        self._move_flames(player)

    def _do_fire_waves(self, player):
        d = self.data
        d["spawn_timer"] = d.get("spawn_timer", 0) + 1
        if d["spawn_timer"] % 50 == 1 and d["wave_count"] < 6:
            d["wave_count"] += 1
            gap_y = player.y + random.randint(-40, 40)
            gap_h = 95
            speed = random.choice([-4.2, 4.2])
            for fy in range(0, HEIGHT + 1, 26):
                if gap_y - gap_h // 2 < fy < gap_y + gap_h // 2:
                    continue
                sx = float(WIDTH + 40) if speed < 0 else float(-40)
                d["flames"].append(self._flame(sx, fy, speed, 0, r=12))
        self._move_flames(player)

    def _do_targeting_flames(self, player):
        d = self.data
        d["spawn_timer"] = d.get("spawn_timer", 0) + 1
        if d["spawn_timer"] % 22 == 1 and d["spawn_count"] < 12:
            d["spawn_count"] += 1
            angle = math.atan2(player.y - self.y, player.x - self.x)
            spread = random.uniform(-0.35, 0.35)
            spd = random.uniform(2.8, 4.0)
            d["flames"].append(
                self._flame(self.x + random.uniform(-20, 20),
                            self.y + random.uniform(-20, 20),
                            math.cos(angle + spread) * spd,
                            math.sin(angle + spread) * spd, r=11))
        for f in d["flames"]:
            if not f["alive"]: continue
            ddx = player.x - f["x"]; ddy = player.y - f["y"]
            dist = math.hypot(ddx, ddy)
            if dist > 1:
                f["vx"] += ddx / dist * 0.10
                f["vy"] += ddy / dist * 0.10
                spd = math.hypot(f["vx"], f["vy"])
                if spd > 5.0:
                    f["vx"] = f["vx"] / spd * 5.0
                    f["vy"] = f["vy"] / spd * 5.0
        self._move_flames(player, mercy=True)

    def _do_crossfire_burst(self, player):
        d = self.data
        d["burst_timer"] = d.get("burst_timer", 0) + 1
        if d["burst_timer"] % 52 == 1 and d["burst_count"] < 4:
            d["burst_count"] += 1
            for pos in [(self.x, self.y), (float(WIDTH // 2), float(HEIGHT // 2))]:
                for k in range(12):
                    angle = k * (math.pi / 6) + random.uniform(-0.05, 0.05)
                    spd = random.uniform(4.0, 6.0)
                    d["flames"].append(
                        self._flame(pos[0], pos[1],
                                    math.cos(angle) * spd, math.sin(angle) * spd, r=11))
        self._move_flames(player)

    def _do_blazing_flower(self, player):
        d = self.data
        d["spawn_timer"] = d.get("spawn_timer", 0) + 1
        d["angle"] = d.get("angle", 0.0) + 0.07
        if d["spawn_timer"] % 5 == 0 and d["rings"] < 45:
            d["rings"] += 1
            base_angle = d["angle"]
            for k in range(7):
                angle = base_angle + k * (2 * math.pi / 7)
                spd = 3.8 + (d["rings"] % 10) * 0.15
                d["flames"].append(
                    self._flame(self.x, self.y,
                                math.cos(angle) * spd, math.sin(angle) * spd, r=10))
        self._move_flames(player)

    def _do_swiping_flames(self, player):
        d = self.data
        d["spawn_timer"] = d.get("spawn_timer", 0) + 1
        if d["spawn_timer"] % 58 == 1 and d["sweep_count"] < 5:
            d["sweep_count"] += 1
            direction = 1 if d["sweep_count"] % 2 == 0 else -1
            gap_y = player.y + random.randint(-40, 40)
            gap_h = 90
            for fy in range(0, HEIGHT + 1, 28):
                if abs(fy - gap_y) < gap_h // 2:
                    continue
                spd = direction * random.uniform(4.5, 6.0)
                sx = float(-40) if direction > 0 else float(WIDTH + 40)
                d["flames"].append(self._flame(sx, float(fy), spd, 0.0, r=13))
        self._move_flames(player)

    def _do_warm_embrace(self, player):
        d = self.data
        if not d["spawned"]:
            d["spawned"] = True
            for _ in range(14):
                d["flames"].append(
                    self._flame(random.randint(30, WIDTH - 30), -40,
                                random.uniform(-0.6, 0.6), random.uniform(3.0, 4.8), r=12))
                d["flames"].append(
                    self._flame(random.randint(30, WIDTH - 30), HEIGHT + 40,
                                random.uniform(-0.6, 0.6), random.uniform(-4.8, -3.0), r=12))
                d["flames"].append(
                    self._flame(-40, random.randint(30, HEIGHT - 30),
                                random.uniform(3.0, 4.8), random.uniform(-0.6, 0.6), r=12))
                d["flames"].append(
                    self._flame(WIDTH + 40, random.randint(30, HEIGHT - 30),
                                random.uniform(-4.8, -3.0), random.uniform(-0.6, 0.6), r=12))
        cx, cy = float(WIDTH // 2), float(HEIGHT // 2)
        for f in d["flames"]:
            if not f["alive"]: continue
            dx = cx - f["x"]; dy = cy - f["y"]
            dist = math.hypot(dx, dy)
            if dist > 1:
                f["vx"] += dx / dist * 0.06
                f["vy"] += dy / dist * 0.06
                spd = math.hypot(f["vx"], f["vy"])
                if spd > 5.2:
                    f["vx"] = f["vx"] / spd * 5.2
                    f["vy"] = f["vy"] / spd * 5.2
        self._move_flames(player, mercy=True)

    def _do_hesitant_flame(self, player):
        d = self.data
        if not d["flames"]:
            angle = math.atan2(player.y - self.y, player.x - self.x)
            d["flames"] = [
                {"x": float(self.x), "y": float(self.y),
                 "vx": math.cos(angle) * 2.8, "vy": math.sin(angle) * 2.8,
                 "r": 26, "alive": True,
                 "phase": "approach", "phase_timer": 75,
                 "target_x": player.x, "target_y": player.y}
            ]
        for f in list(d["flames"]):
            if not f["alive"]: continue
            ph = f.get("phase", "approach")
            if ph == "approach":
                f["phase_timer"] -= 1
                f["x"] += f["vx"]; f["y"] += f["vy"]
                if f["phase_timer"] <= 0:
                    f["phase"] = "pause"; f["phase_timer"] = 45
                    f["vx"] = 0.0; f["vy"] = 0.0
                    f["target_x"] = player.x; f["target_y"] = player.y
            elif ph == "pause":
                f["phase_timer"] -= 1
                if f["phase_timer"] <= 0:
                    f["phase"] = "rush"
                    ddx = f["target_x"] - f["x"]; ddy = f["target_y"] - f["y"]
                    dist = math.hypot(ddx, ddy)
                    if dist > 1:
                        f["vx"] = ddx / dist * 8.5; f["vy"] = ddy / dist * 8.5
                    else:
                        f["vx"] = 8.5; f["vy"] = 0.0
            elif ph == "rush":
                f["x"] += f["vx"]; f["y"] += f["vy"]
                if f["x"] < -100 or f["x"] > WIDTH + 100 or f["y"] < -100 or f["y"] > HEIGHT + 100:
                    f["alive"] = False
            if f["alive"] and player.hit_cooldown <= 0:
                if math.hypot(f["x"] - player.x, f["y"] - player.y) < f["r"] + player.size * 0.45:
                    player.take_damage(1)
        d["flames"] = [f for f in d["flames"] if f["alive"]]

    def _do_crossfire_hands(self, player):
        d = self.data
        d["spawn_timer"] = d.get("spawn_timer", 0) + 1
        if d["spawn_timer"] % 7 == 0:
            for origin, base_angle in [
                ((float(30), float(HEIGHT // 2)), 0.0),
                ((float(WIDTH - 30), float(HEIGHT // 2)), math.pi),
            ]:
                for spread in (-0.25, 0.0, 0.25):
                    angle = base_angle + spread
                    spd = random.uniform(4.0, 5.5)
                    d["flames"].append(
                        self._flame(origin[0], origin[1],
                                    math.cos(angle) * spd, math.sin(angle) * spd, r=10))
        self._move_flames(player)

    def _do_tracing_fire(self, player):
        d = self.data
        d["trail"].append({"x": player.x, "y": player.y})
        if len(d["trail"]) > 90:
            d["trail"].pop(0)
        d["spawn_timer"] = d.get("spawn_timer", 0) + 1
        if d["spawn_timer"] % 16 == 0 and len(d["trail"]) >= 65:
            pos = d["trail"][0]
            for k in range(6):
                angle = k * (math.pi / 3) + random.uniform(-0.1, 0.1)
                spd = random.uniform(2.5, 4.0)
                d["flames"].append(
                    self._flame(pos["x"], pos["y"],
                                math.cos(angle) * spd, math.sin(angle) * spd, r=10))
        self._move_flames(player, mercy=True)

    def _do_mercy_pattern(self, player):
        d = self.data
        d["spawn_timer"] = d.get("spawn_timer", 0) + 1
        if d["spawn_timer"] % 18 == 1:
            side = random.choice(["left", "right", "top", "bottom"])
            if side == "left":
                sx, sy = -30.0, float(random.randint(30, HEIGHT - 30))
            elif side == "right":
                sx, sy = float(WIDTH + 30), float(random.randint(30, HEIGHT - 30))
            elif side == "top":
                sx, sy = float(random.randint(30, WIDTH - 30)), -30.0
            else:
                sx, sy = float(random.randint(30, WIDTH - 30)), float(HEIGHT + 30)
            angle = random.uniform(0, 2 * math.pi)
            spd = random.uniform(2.5, 3.5)
            d["flames"].append(
                self._flame(sx, sy, math.cos(angle) * spd, math.sin(angle) * spd, r=10))
        self._move_flames(player, mercy=True)

    def take_damage(self, amount):
        self.hp = max(0, self.hp - amount)
        for _ in range(10):
            angle = random.uniform(0, 2 * math.pi)
            self.hit_particles.append({
                "x": self.x, "y": self.y,
                "vx": math.cos(angle) * random.uniform(2, 6),
                "vy": math.sin(angle) * random.uniform(2, 6),
                "life": random.randint(12, 22),
            })

    def draw(self, small_font, mercy_active=False):
        _OR  = (255, 140,  50)
        _YEL = (255, 220,  60)
        _WHT = (255, 255, 255)

        # ── 보스 스프라이트 ──
        sprite_t = pygame.transform.scale(TORIEL_IMAGE, (90, 100))
        screen.blit(sprite_t, (int(self.x) - 45, int(self.y) - 50))

        # ── 체력바 ──
        bar_w = 220
        bar_x = int(self.x) - bar_w // 2
        bar_y = int(self.y) - 76
        pygame.draw.rect(screen, (50, 50, 50), (bar_x, bar_y, bar_w, 10))
        hp_ratio = max(0.0, self.hp / self.max_hp)
        pygame.draw.rect(screen, _OR, (bar_x, bar_y, int(bar_w * hp_ratio), 10))
        hp_t = small_font.render(f"TORIEL  HP {self.hp}/{self.max_hp}", True, _OR)
        screen.blit(hp_t, (bar_x, bar_y - 18))

        # ── 인용구 ──
        if self.quote_timer > 0 and self.pattern in self.PATTERN_QUOTE:
            alpha = min(255, self.quote_timer * 8)
            qt = small_font.render(self.PATTERN_QUOTE[self.pattern], True, (255, 210, 140))
            qt.set_alpha(alpha)
            screen.blit(qt, (WIDTH // 2 - qt.get_width() // 2, int(self.y) + self.size // 2 + 12))

        # ── 자비 표시 ──
        if mercy_active:
            mt = small_font.render("* ...I won't hurt you.", True, (255, 200, 120))
            screen.blit(mt, (WIDTH // 2 - mt.get_width() // 2, 12))

        # ── 화염구 그리기 ──
        for f in self.data.get("flames", []):
            if not f.get("alive", True): continue
            fx, fy_i = int(f["x"]), int(f["y"])
            fr = int(f["r"])
            gsurf = pygame.Surface((fr * 4 + 1, fr * 4 + 1), pygame.SRCALPHA)
            pygame.draw.circle(gsurf, (255, 120, 40, 55), (fr * 2, fr * 2), fr * 2)
            screen.blit(gsurf, (fx - fr * 2, fy_i - fr * 2),
                        special_flags=pygame.BLEND_RGBA_ADD)
            pygame.draw.circle(screen, _OR,  (fx, fy_i), fr)
            pygame.draw.circle(screen, _YEL, (fx, fy_i), max(1, fr - 4))
            pygame.draw.circle(screen, _WHT, (fx, fy_i), max(1, fr - 8))

        for bf in self.data.get("big_flames", []):
            if not bf.get("alive", True): continue
            fx, fy_i = int(bf["x"]), int(bf["y"])
            fr = int(bf["r"])
            gsurf = pygame.Surface((fr * 4 + 1, fr * 4 + 1), pygame.SRCALPHA)
            pygame.draw.circle(gsurf, (255, 80, 20, 80), (fr * 2, fr * 2), fr * 2)
            screen.blit(gsurf, (fx - fr * 2, fy_i - fr * 2),
                        special_flags=pygame.BLEND_RGBA_ADD)
            pygame.draw.circle(screen, (255,  80,  20), (fx, fy_i), fr)
            pygame.draw.circle(screen, _OR,              (fx, fy_i), max(1, fr - 6))
            pygame.draw.circle(screen, _YEL,             (fx, fy_i), max(1, fr - 12))

        # ── 취약 상태 표시 ──
        if self.state == "vulnerable":
            ratio = self.timer / 90
            vsurf = pygame.Surface((self.size + 20, self.size + 20), pygame.SRCALPHA)
            pygame.draw.rect(vsurf, (80, 255, 80, int(180 * ratio)),
                             (0, 0, self.size + 20, self.size + 20), 3)
            screen.blit(vsurf, (int(self.x) - (self.size + 20) // 2,
                                 int(self.y) - (self.size + 20) // 2))

        # ── 피격 파티클 ──
        for pt in self.hit_particles:
            ratio_p = pt["life"] / 22
            pygame.draw.circle(screen, (255, int(180 * ratio_p), 60),
                               (int(pt["x"]), int(pt["y"])), max(1, int(5 * ratio_p)))


# ═══════════════════════════════════════════════════════════════════
#  UNDYNE BOSS
# ═══════════════════════════════════════════════════════════════════
class UndyneBoss:
    """언다인 보스. 녹색/빨간 영혼 전환 패턴."""
    name = "UNDYNE"

    TURN_SEQ = [
        "basic_spears",      # 1  green
        "rising_spears",     # 2  red
        "fast_spears",       # 3  green
        "circle_trap",       # 4  red
        "yellow_spears",     # 5  green
        "targeting_spears",  # 6  red
        "mixed_spears",      # 7  green
        "spear_tunnel",      # 8  red
        "rotating_ring",     # 9  green
        "yellow_barrage",    # 10 green
    ]
    LOOP_SEQ = [
        "basic_spears", "targeting_spears", "fast_spears",
        "circle_trap", "mixed_spears", "rotating_ring",
        "rising_spears", "yellow_spears", "yellow_barrage",
        "spear_tunnel",
    ]
    GREEN_SOUL_PATS = frozenset({
        "basic_spears", "fast_spears", "yellow_spears",
        "mixed_spears", "rotating_ring", "yellow_barrage",
    })
    PATTERN_QUOTE = {
        "basic_spears":      "* Feel the power of my spear!",
        "rising_spears":     "* Watch your feet, human!",
        "fast_spears":       "* Try to keep up!",
        "circle_trap":       "* You can't escape!",
        "yellow_spears":     "* These ones have a TWIST!",
        "targeting_spears":  "* Your movements are predictable!",
        "mixed_spears":      "* Don't blink!",
        "spear_tunnel":      "* Run all you want!",
        "rotating_ring":     "* Now you're REALLY in trouble!",
        "yellow_barrage":    "* WITNESS MY FULL POWER!",
    }

    def __init__(self):
        self.x = float(WIDTH * 0.74)
        self.y = float(HEIGHT // 2)
        self.size = 90
        self.hp = 100
        self.max_hp = 100
        self.state = "idle"
        self.timer = 40
        self.pattern = None
        self.data = {}
        self.turn = 0
        self.hit_particles = []
        self.quote_timer = 0

    def get_rect(self):
        return pygame.Rect(int(self.x) - self.size // 2,
                           int(self.y) - self.size // 2, self.size, self.size)

    def is_vulnerable(self):
        return self.state == "vulnerable"

    def is_green_soul(self):
        return self.pattern in self.GREEN_SOUL_PATS

    def start_pattern(self):
        if self.turn < len(self.TURN_SEQ):
            self.pattern = self.TURN_SEQ[self.turn]
        else:
            choices = [p for p in self.LOOP_SEQ if p != self.pattern] or self.LOOP_SEQ
            self.pattern = random.choice(choices)
        self.turn += 1
        self.state = "telegraph"
        self.data = {}
        self.quote_timer = 80

        tele = {"basic_spears": 30, "rising_spears": 25, "fast_spears": 30,
                "circle_trap": 30, "yellow_spears": 35, "targeting_spears": 28,
                "mixed_spears": 35, "spear_tunnel": 25, "rotating_ring": 35,
                "yellow_barrage": 35}
        act  = {"basic_spears": 240, "rising_spears": 220, "fast_spears": 200,
                "circle_trap": 200, "yellow_spears": 250, "targeting_spears": 220,
                "mixed_spears": 260, "spear_tunnel": 240, "rotating_ring": 260,
                "yellow_barrage": 280}
        self.timer = tele.get(self.pattern, 28)
        self.data["_act"] = act.get(self.pattern, 220)

        p = self.pattern
        if p in ("basic_spears", "fast_spears", "yellow_spears",
                 "mixed_spears", "yellow_barrage"):
            self.data.update({"spears": [], "spawn_timer": 0, "spawn_count": 0})
        elif p == "rising_spears":
            self.data.update({"spears": [], "warnings": [],
                              "spawn_timer": 0, "spawn_count": 0})
        elif p == "circle_trap":
            self.data.update({"spears": [], "phase": "warn",
                              "phase_timer": 55, "radius": 200.0,
                              "cx": 0.0, "cy": 0.0})
        elif p == "targeting_spears":
            self.data.update({"spears": [], "warnings": [],
                              "spawn_timer": 0, "spawn_count": 0})
        elif p == "spear_tunnel":
            self.data.update({"spears": [], "spawn_timer": 0, "spawn_count": 0,
                              "undyne_x": float(WIDTH + 80)})
        elif p == "rotating_ring":
            self.data.update({"spears": [], "angle": 0.0, "radius": 190.0,
                              "phase": "spin", "spin_timer": 150})

    def update(self, player, shield_dir):
        tx, ty = float(WIDTH * 0.74), float(HEIGHT // 2)
        self.x += (tx - self.x) * 0.018
        self.y += (ty - self.y) * 0.018
        if self.quote_timer > 0:
            self.quote_timer -= 1

        if self.state == "idle":
            self.timer -= 1
            if self.timer <= 0:
                self.start_pattern()
        elif self.state == "telegraph":
            self.timer -= 1
            if self.timer <= 0:
                self.state = "active"
                self.timer = self.data.pop("_act", 220)
        elif self.state == "active":
            self.timer -= 1
            p = self.pattern
            if   p == "basic_spears":     self._do_green_spears(player, shield_dir, fast=False, yellow=False, mixed=False)
            elif p == "fast_spears":      self._do_green_spears(player, shield_dir, fast=True,  yellow=False, mixed=False)
            elif p == "yellow_spears":    self._do_green_spears(player, shield_dir, fast=False, yellow=True,  mixed=False)
            elif p == "mixed_spears":     self._do_green_spears(player, shield_dir, fast=False, yellow=False, mixed=True)
            elif p == "yellow_barrage":   self._do_green_spears(player, shield_dir, fast=True,  yellow=True,  mixed=True)
            elif p == "rising_spears":    self._do_rising_spears(player)
            elif p == "circle_trap":      self._do_circle_trap(player)
            elif p == "targeting_spears": self._do_targeting_spears(player)
            elif p == "spear_tunnel":     self._do_spear_tunnel(player)
            elif p == "rotating_ring":    self._do_rotating_ring(player, shield_dir)
            if self.timer <= 0:
                self.state = "vulnerable"
                self.timer = 90
                self.data = {}
        elif self.state == "vulnerable":
            self.timer -= 1
            if self.timer <= 0:
                self.state = "idle"
                self.timer = 22

        for pt in self.hit_particles:
            pt["x"] += pt["vx"]; pt["y"] += pt["vy"]; pt["life"] -= 1
        self.hit_particles = [pt for pt in self.hit_particles if pt["life"] > 0]

    # ── GREEN SOUL helpers ────────────────────────────────────────

    _GS_CX = int(WIDTH * 0.22)
    _GS_CY = int(HEIGHT // 2)

    def _gs_spear(self, from_dir, yellow=False, fast=False):
        cx, cy = self._GS_CX, self._GS_CY
        spd = 7.0 if fast else 5.0
        wt  = 28  if fast else 42
        if   from_dir == 0: x, y, vx, vy = float(cx),        float(-20),       0.0,  spd
        elif from_dir == 1: x, y, vx, vy = float(WIDTH + 20), float(cy),       -spd, 0.0
        elif from_dir == 2: x, y, vx, vy = float(cx),        float(HEIGHT+20),  0.0, -spd
        else:               x, y, vx, vy = float(-20),        float(cy),        spd, 0.0
        return {"x": x, "y": y, "vx": vx, "vy": vy, "from_dir": from_dir,
                "yellow": yellow, "phase": "warn", "warn_timer": wt,
                "alive": True}

    def _do_green_spears(self, player, shield_dir, fast, yellow, mixed):
        d = self.data
        max_c = 14 if fast else 10
        interval = 18 if fast else 36
        d["spawn_timer"] -= 1
        if d["spawn_timer"] <= 0 and d["spawn_count"] < max_c:
            # 이미 날아오고 있는 창이 있으면 같은 방향으로만 스폰해서
            # 여러 방향에서 동시에 창이 날아오지 않게 한다.
            active_dirs = {s["from_dir"] for s in d["spears"] if s["alive"]}
            fd = next(iter(active_dirs)) if active_dirs else random.randint(0, 3)
            is_y = yellow or (mixed and random.random() < 0.45)
            d["spears"].append(self._gs_spear(fd, yellow=is_y, fast=fast))
            d["spawn_count"] += 1
            d["spawn_timer"] = interval
        self._tick_green_spears(player, shield_dir)
        if d["spawn_count"] >= max_c and not d["spears"]:
            self.timer = 0

    def _tick_green_spears(self, player, shield_dir):
        cx, cy = self._GS_CX, self._GS_CY
        for sp in self.data["spears"]:
            if not sp["alive"]: continue
            if sp["phase"] == "warn":
                sp["warn_timer"] -= 1
                if sp["warn_timer"] <= 0:
                    sp["phase"] = "move"
            else:
                sp["x"] += sp["vx"]; sp["y"] += sp["vy"]
                pr = pygame.Rect(cx - 14, cy - 14, 28, 28)
                sr = pygame.Rect(int(sp["x"]) - 8, int(sp["y"]) - 8, 16, 16)
                if sr.colliderect(pr):
                    # 노란 창은 되돌아오지 않고 그대로 반대편까지 날아가 반대 방향에서 공격한다.
                    req_dir = (sp["from_dir"] + 2) % 4 if sp["yellow"] else sp["from_dir"]
                    if shield_dir != req_dir:
                        player.take_damage(1)
                    sp["alive"] = False
                if (sp["x"] < -60 or sp["x"] > WIDTH + 60 or
                        sp["y"] < -60 or sp["y"] > HEIGHT + 60):
                    sp["alive"] = False
        self.data["spears"] = [s for s in self.data["spears"] if s["alive"]]

    # ── RED SOUL helpers ──────────────────────────────────────────

    def _do_rising_spears(self, player):
        d = self.data
        max_c = 10; d["spawn_timer"] -= 1
        if d["spawn_timer"] <= 0 and d["spawn_count"] < max_c:
            wx = random.randint(60, int(WIDTH * 0.55) - 60)
            d["warnings"].append({"x": wx, "timer": 38, "spawned": False})
            d["spawn_count"] += 1; d["spawn_timer"] = 38
        for w in d["warnings"]:
            if w["timer"] > 0:
                w["timer"] -= 1
            elif not w["spawned"]:
                w["spawned"] = True
                d["spears"].append({"x": float(w["x"]), "y": float(HEIGHT + 10),
                                   "vx": 0.0, "vy": -7.0, "alive": True})
        for sp in d["spears"]:
            if not sp["alive"]: continue
            sp["y"] += sp["vy"]
            if sp["vy"] < 0 and sp["y"] < -20: sp["alive"] = False
            sr = pygame.Rect(int(sp["x"]) - 8, int(sp["y"]) - 8, 16, 16)
            if sr.colliderect(player.get_rect()):
                player.take_damage(1); sp["alive"] = False
        d["spears"]   = [s for s in d["spears"]   if s["alive"]]
        d["warnings"] = [w for w in d["warnings"] if not (w["timer"] <= 0 and w["spawned"])]
        if d["spawn_count"] >= max_c and not d["spears"]:
            self.timer = 0

    def _do_circle_trap(self, player):
        d = self.data; n = 8
        if d["phase"] == "warn":
            d["phase_timer"] -= 1
            if d["phase_timer"] <= 0:
                d["cx"] = float(player.x); d["cy"] = float(player.y)
                r = d["radius"]
                for i in range(n):
                    a = 2 * math.pi * i / n
                    d["spears"].append({"x": d["cx"] + r * math.cos(a),
                                        "y": d["cy"] + r * math.sin(a),
                                        "angle": a, "alive": True})
                d["phase"] = "close"
        elif d["phase"] == "close":
            d["radius"] = max(0.0, d["radius"] - 2.2)
            r = d["radius"]; cx2 = d["cx"]; cy2 = d["cy"]
            for sp in d["spears"]:
                if not sp["alive"]: continue
                sp["x"] = cx2 + r * math.cos(sp["angle"])
                sp["y"] = cy2 + r * math.sin(sp["angle"])
                sr = pygame.Rect(int(sp["x"]) - 12, int(sp["y"]) - 12, 24, 24)
                if sr.colliderect(player.get_rect()):
                    player.take_damage(2); sp["alive"] = False
            if d["radius"] <= 18:
                for sp in d["spears"]: sp["alive"] = False
                self.timer = 0
            d["spears"] = [s for s in d["spears"] if s["alive"]]

    def _do_targeting_spears(self, player):
        d = self.data; max_c = 12; d["spawn_timer"] -= 1
        if d["spawn_timer"] <= 0 and d["spawn_count"] < max_c:
            wx = max(40, min(int(WIDTH * 0.55) - 40,
                            int(player.x) + random.randint(-50, 50)))
            d["warnings"].append({"x": wx, "timer": 42, "spawned": False})
            d["spawn_count"] += 1; d["spawn_timer"] = 34
        for w in d["warnings"]:
            if w["timer"] > 0:
                w["timer"] -= 1
            elif not w["spawned"]:
                w["spawned"] = True
                ang = random.uniform(-0.3, 0.3)
                d["spears"].append({"x": float(w["x"]), "y": float(-20),
                                   "vx": 7.0 * math.sin(ang),
                                   "vy": 7.0 * math.cos(ang), "alive": True})
        for sp in d["spears"]:
            if not sp["alive"]: continue
            sp["x"] += sp["vx"]; sp["y"] += sp["vy"]
            sr = pygame.Rect(int(sp["x"]) - 8, int(sp["y"]) - 8, 16, 16)
            if sr.colliderect(player.get_rect()):
                player.take_damage(1); sp["alive"] = False
            if sp["y"] > HEIGHT + 30 or sp["x"] < -30 or sp["x"] > WIDTH + 30:
                sp["alive"] = False
        d["spears"]   = [s for s in d["spears"]   if s["alive"]]
        d["warnings"] = [w for w in d["warnings"] if not (w["timer"] <= 0 and w["spawned"])]
        if d["spawn_count"] >= max_c and not d["spears"] and not d["warnings"]:
            self.timer = 0

    def _do_spear_tunnel(self, player):
        d = self.data; max_c = 18; d["spawn_timer"] -= 1
        d["undyne_x"] += (player.x - 100 - d["undyne_x"]) * 0.04
        if d["spawn_timer"] <= 0 and d["spawn_count"] < max_c:
            wx = max(30, min(int(WIDTH * 0.55) - 30,
                            int(d["undyne_x"]) + random.randint(-40, 40)))
            d["spears"].append({"x": float(wx), "y": float(HEIGHT + 10),
                               "vx": 0.0, "vy": -6.5, "alive": True})
            d["spawn_count"] += 1; d["spawn_timer"] = 26
        for sp in d["spears"]:
            if not sp["alive"]: continue
            sp["y"] += sp["vy"]
            sr = pygame.Rect(int(sp["x"]) - 8, int(sp["y"]) - 8, 16, 16)
            if sr.colliderect(player.get_rect()):
                player.take_damage(1); sp["alive"] = False
            if sp["y"] < -30: sp["alive"] = False
        d["spears"] = [s for s in d["spears"] if s["alive"]]
        if d["spawn_count"] >= max_c and not d["spears"]:
            self.timer = 0

    def _do_rotating_ring(self, player, shield_dir):
        d = self.data; n = 6
        cx, cy = self._GS_CX, self._GS_CY
        d["angle"] += 0.035
        d["spin_timer"] -= 1
        d["radius"] = max(28.0, d["radius"] - 0.38)
        r = d["radius"]
        if not d["spears"]:
            for i in range(n):
                d["spears"].append({"idx": i, "x": 0.0, "y": 0.0, "alive": True})
        for sp in d["spears"]:
            if not sp["alive"]: continue
            a = d["angle"] + 2 * math.pi * sp["idx"] / n
            sp["x"] = cx + r * math.cos(a)
            sp["y"] = cy + r * math.sin(a)
            pr = pygame.Rect(cx - 14, cy - 14, 28, 28)
            sr = pygame.Rect(int(sp["x"]) - 10, int(sp["y"]) - 10, 20, 20)
            if sr.colliderect(pr):
                dx = sp["x"] - cx; dy = sp["y"] - cy
                needed = (1 if dx > 0 else 3) if abs(dx) > abs(dy) else (2 if dy > 0 else 0)
                if shield_dir != needed:
                    player.take_damage(1)
                sp["alive"] = False
        d["spears"] = [s for s in d["spears"] if s["alive"]]
        if d["spin_timer"] <= 0 or not d["spears"]:
            self.timer = 0

    def take_damage(self, amount):
        if not self.is_vulnerable(): return
        self.hp -= amount
        for _ in range(8):
            a = random.uniform(0, 2 * math.pi); spd = random.uniform(2, 6)
            self.hit_particles.append({"x": float(self.x), "y": float(self.y),
                                       "vx": math.cos(a) * spd, "vy": math.sin(a) * spd,
                                       "life": random.randint(12, 22), "max_life": 22})

    def draw(self, small_font, shield_dir=0):
        # Sprite
        sprite = pygame.transform.scale(UNDYNE_IMAGE, (self.size, self.size))
        if self.is_vulnerable():
            tinted = sprite.copy()
            tinted.fill((255, 230, 80, 0), special_flags=pygame.BLEND_RGBA_ADD)
            sprite = tinted
        screen.blit(sprite, (int(self.x) - self.size // 2, int(self.y) - self.size // 2))

        p = self.pattern
        green = p in self.GREEN_SOUL_PATS

        if green:
            cx, cy = self._GS_CX, self._GS_CY
            # Soul diamond
            soul_s = pygame.Surface((18, 18), pygame.SRCALPHA)
            pygame.draw.polygon(soul_s, (80, 230, 80), [(9, 0), (18, 9), (9, 18), (0, 9)])
            screen.blit(soul_s, (cx - 9, cy - 9))
            # Shield
            sh_col = (60, 210, 60); sw = 32; sh_t = 10
            if   shield_dir == 0: pygame.draw.rect(screen, sh_col, (cx - sw//2, cy - 24, sw, sh_t))
            elif shield_dir == 1: pygame.draw.rect(screen, sh_col, (cx + 14, cy - sw//2, sh_t, sw))
            elif shield_dir == 2: pygame.draw.rect(screen, sh_col, (cx - sw//2, cy + 14, sw, sh_t))
            else:                 pygame.draw.rect(screen, sh_col, (cx - 24, cy - sw//2, sh_t, sw))
            # Spears (green soul)
            for sp in self.data.get("spears", []):
                if not sp.get("alive", True): continue
                col = (255, 220, 0) if sp.get("yellow") else (80, 255, 100)
                if sp.get("phase") == "warn":
                    fd = sp.get("from_dir", 0)
                    wx2 = cx if fd in (0, 2) else (WIDTH - 8 if fd == 1 else 8)
                    wy2 = cy if fd in (1, 3) else (8 if fd == 0 else HEIGHT - 8)
                    alpha_w = max(0, 255 - sp.get("warn_timer", 0) * 5)
                    ws = pygame.Surface((20, 20), pygame.SRCALPHA)
                    ws.fill((*col, alpha_w)); screen.blit(ws, (wx2 - 10, wy2 - 10))
                elif "vx" in sp and "vy" in sp:
                    # directed spear: draw as line + tip
                    ex, ey = int(sp["x"]), int(sp["y"])
                    vx2, vy2 = sp["vx"], sp["vy"]
                    spd2 = max(0.1, math.hypot(vx2, vy2)); lng = 24
                    dx2, dy2 = int(vx2 / spd2 * lng), int(vy2 / spd2 * lng)
                    pygame.draw.line(screen, col, (ex, ey), (ex + dx2, ey + dy2), 4)
                    pygame.draw.circle(screen, WHITE, (ex, ey), 5)
                else:
                    # rotating_ring spear: no direction, draw as glowing orb
                    ex, ey = int(sp.get("x", 0)), int(sp.get("y", 0))
                    pygame.draw.circle(screen, col, (ex, ey), 9)
                    pygame.draw.circle(screen, WHITE, (ex, ey), 4)
        else:
            # Red soul spears
            for sp in self.data.get("spears", []):
                if not sp.get("alive", True): continue
                ex, ey = int(sp["x"]), int(sp["y"])
                vx2 = sp.get("vx", 0.0); vy2 = sp.get("vy", 0.0)
                spd2 = max(0.1, math.hypot(vx2, vy2)); lng = 26
                dx2 = int(vx2 / spd2 * lng); dy2 = int(vy2 / spd2 * lng)
                col = (255, 80, 80)
                pygame.draw.line(screen, col, (ex, ey), (ex + dx2, ey + dy2), 5)
                pygame.draw.circle(screen, (255, 180, 180), (ex, ey), 5)
            # Rising/targeting warnings
            for w in self.data.get("warnings", []):
                wx2 = int(w["x"]); t2 = w["timer"]
                alpha_w = max(0, min(180, (40 - t2) * 5))
                ws2 = pygame.Surface((14, HEIGHT), pygame.SRCALPHA)
                ws2.fill((255, 80, 80, alpha_w))
                screen.blit(ws2, (wx2 - 7, 0))
            # Circle trap
            if p == "circle_trap":
                for sp in self.data.get("spears", []):
                    if not sp.get("alive", True): continue
                    pygame.draw.circle(screen, (255, 80, 80),
                                       (int(sp["x"]), int(sp["y"])), 9)
            # Spear tunnel: mini undyne sprite chasing
            if p == "spear_tunnel":
                ux = int(self.data.get("undyne_x", WIDTH))
                mini = pygame.transform.scale(UNDYNE_IMAGE, (48, 68))
                screen.blit(mini, (ux - 24, HEIGHT // 2 - 34))

        # Shield direction hint
        if green:
            dir_names = ["↑ UP", "→ RIGHT", "↓ DOWN", "← LEFT"]
            hint_t = small_font.render(f"Shield: {dir_names[shield_dir]}", True, (80, 230, 80))
            screen.blit(hint_t, (12, HEIGHT - 52))
            ctrl_t = small_font.render("Arrow keys / WASD = shield direction", True, (60, 160, 60))
            screen.blit(ctrl_t, (12, HEIGHT - 32))

        # Pattern quote
        if self.quote_timer > 0 and self.pattern:
            q = self.PATTERN_QUOTE.get(self.pattern, "")
            if q:
                q_surf = small_font.render(q, True, (100, 255, 180))
                q_surf.set_alpha(min(255, self.quote_timer * 3))
                screen.blit(q_surf, (WIDTH // 2 - q_surf.get_width() // 2, HEIGHT - 58))

        # Boss HP bar
        bar_w = 200
        pygame.draw.rect(screen, (60, 60, 60), (WIDTH // 2 - bar_w // 2, 16, bar_w, 16))
        pygame.draw.rect(screen, (80, 160, 255),
                         (WIDTH // 2 - bar_w // 2, 16,
                          int(bar_w * max(self.hp, 0) / self.max_hp), 16))
        nt = small_font.render(self.name, True, WHITE)
        screen.blit(nt, (WIDTH // 2 - nt.get_width() // 2, 34))

        for pt in self.hit_particles:
            ratio = pt["life"] / pt["max_life"]
            pygame.draw.circle(screen, (int(255 * ratio), int(140 * ratio), int(60 * ratio)),
                               (int(pt["x"]), int(pt["y"])), max(1, int(5 * ratio)))


# ═══════════════════════════════════════════════════════════════════
#  SANS BOSS
# ═══════════════════════════════════════════════════════════════════
class SansBoss:
    """히든2 보스: 샌즈. 순서형 13턴 패턴."""

    name = "SANS"

    TURN_SEQ = [
        "first_turn", "bone_wave", "blue_white_bones", "blaster_circle",
        "slam_gravity", "short_bone", "bone_platforms", "spare",
        "random_slams", "fast_blasters", "rotating_blasters", "bone_gap",
        "final_overdrive",
    ]
    PHASE2_SEQ = [
        "random_slams", "fast_blasters", "rotating_blasters",
        "bone_gap", "final_overdrive",
    ]

    def __init__(self):
        self.x = float(WIDTH * 0.72)
        self.y = float(HEIGHT // 2)
        self.size = 75
        self.hp = 120
        self.max_hp = 120
        self.state = "idle"
        self.timer = 45
        self.pattern = None
        self.data = {}
        self.turn = 0
        self.phase2 = False
        self.hit_particles = []
        self.eye_particles = []
        self.eye_anim_t = 0

    def get_rect(self):
        return pygame.Rect(int(self.x) - self.size // 2, int(self.y) - self.size // 2,
                           self.size, self.size)

    def is_vulnerable(self):
        return self.state == "vulnerable" or (
            self.pattern == "spare" and self.state == "active"
        )

    def start_pattern(self):
        self.turn += 1
        if self.turn <= 13:
            self.pattern = self.TURN_SEQ[self.turn - 1]
        else:
            self.pattern = self.PHASE2_SEQ[(self.turn - 9) % len(self.PHASE2_SEQ)]
        if self.turn >= 9:
            self.phase2 = True

        self.state = "telegraph"
        self.data = {}

        tele = {
            "first_turn": 25, "bone_wave": 28, "blue_white_bones": 28,
            "blaster_circle": 35, "slam_gravity": 22, "short_bone": 22,
            "bone_platforms": 28, "spare": 20,
            "random_slams": 18, "fast_blasters": 22, "rotating_blasters": 28,
            "bone_gap": 28, "final_overdrive": 18,
        }
        self.timer = tele.get(self.pattern, 22)

        act = {
            "first_turn": 220, "bone_wave": 280, "blue_white_bones": 280,
            "blaster_circle": 250, "slam_gravity": 240, "short_bone": 220,
            "bone_platforms": 200, "spare": 300,
            "random_slams": 220, "fast_blasters": 220, "rotating_blasters": 200,
            "bone_gap": 260, "final_overdrive": 300,
        }
        self.data["_act"] = act.get(self.pattern, 200)

        if self.pattern in ("bone_wave", "short_bone", "blue_white_bones"):
            self.data.update({"bones": [], "spawn_timer": 0, "spawn_count": 0})
        elif self.pattern == "blaster_circle":
            cx, cy = int(self.x - 160), HEIGHT // 2
            r = 185
            self.data["blasters"] = [
                {"x": float(cx + r * math.cos(2 * math.pi * i / 5)),
                 "y": float(cy + r * math.sin(2 * math.pi * i / 5)),
                 "aim": math.pi + 2 * math.pi * i / 5,
                 "charge_t": 28, "delay": i * 22, "alive": True}
                for i in range(5)
            ]
        elif self.pattern in ("slam_gravity", "random_slams"):
            self.data.update({
                "slam_count": 0,
                "max_slams": 4 if self.pattern == "slam_gravity" else 6,
                "slam_phase": "waiting", "slam_dir": None,
                "slam_timer": 0, "spikes": [],
            })
        elif self.pattern == "bone_gap":
            self.data.update({"walls": [], "spawn_timer": 0, "spawn_count": 0, "max_walls": 5})
        elif self.pattern == "bone_platforms":
            self.data.update({
                "platforms": [
                    {"y": float(HEIGHT // 4),     "x": float(WIDTH // 4),      "vx": 2.5},
                    {"y": float(HEIGHT // 2),     "x": float(WIDTH // 2 - 55), "vx": -2.2},
                    {"y": float(3 * HEIGHT // 4), "x": float(3 * WIDTH // 4),  "vx": 1.8},
                ],
                "spike_y": float(HEIGHT), "pw": 110, "ph": 14,
            })
        elif self.pattern == "first_turn":
            self.data.update({
                "sub_phase": "gravity", "sub_timer": 38,
                "gravity_dir": random.choice(["left", "right", "up", "down"]),
                "spike_wall": None, "spikes_pos": [],
                "blasters": [],
                "wall_x": float(WIDTH + 20),
                "gap_y": random.randint(90, HEIGHT - 90),
            })
        elif self.pattern == "spare":
            self.data.update({"spare_timer": 300, "attacked": False})
        elif self.pattern == "fast_blasters":
            self.data.update({
                "blasters": [], "spawn_timer": 0, "total_spawned": 0,
                "max_blasters": 6 if not self.phase2 else 8,
            })
        elif self.pattern == "rotating_blasters":
            cx2 = float(self.x - 150)
            cy2 = float(HEIGHT // 2)
            r2 = 180
            self.data.update({
                "orbit_angle": 0.0, "orbit_r": r2,
                "angular_speed": 0.022 if not self.phase2 else 0.032,
                "blasters": [
                    {"offset": i * 2 * math.pi / 3, "fire_cd": 45, "beam_t": 0,
                     "bx": cx2 + r2 * math.cos(i * 2 * math.pi / 3),
                     "by": cy2 + r2 * math.sin(i * 2 * math.pi / 3),
                     "aim": math.pi + i * 2 * math.pi / 3}
                    for i in range(3)
                ],
                "cx": cx2, "cy": cy2,
            })
        elif self.pattern == "final_overdrive":
            self.data.update({
                "sub_phase": "bone_tunnel", "sub_timer": 85,
                "bones": [], "blasters": [], "spawn_timer": 0,
                "slams_done": 0, "slam_phase": "waiting",
                "slam_timer": 0, "slam_dir": None, "spikes": [],
            })

    def update(self, player):
        tx, ty = float(WIDTH * 0.72), float(HEIGHT // 2)
        self.x += (tx - self.x) * 0.015
        self.y += (ty - self.y) * 0.015

        if self.state == "idle":
            self.timer -= 1
            if self.timer <= 0:
                self.start_pattern()

        elif self.state == "telegraph":
            self.timer -= 1
            if self.timer <= 0:
                self.state = "active"
                self.timer = self.data.pop("_act", 200)

        elif self.state == "active":
            self.timer -= 1
            p = self.pattern
            if p == "first_turn":              self._do_first_turn(player)
            elif p in ("bone_wave","short_bone"): self._do_bones_wave(player, p)
            elif p == "blue_white_bones":      self._do_blue_white(player)
            elif p == "blaster_circle":
                self._fire_blasters(player, self.data["blasters"])
                if all(not b["alive"] for b in self.data["blasters"]):
                    self.timer = 0
            elif p in ("slam_gravity","random_slams"): self._do_slams(player, p)
            elif p == "bone_platforms":        self._do_platforms(player)
            elif p == "spare":                 self.data["spare_timer"] -= 1
            elif p == "fast_blasters":         self._do_fast_blasters(player)
            elif p == "rotating_blasters":     self._do_rotating(player)
            elif p == "bone_gap":              self._do_bone_gap(player)
            elif p == "final_overdrive":       self._do_final(player)

            if self.timer <= 0 and p != "spare":
                self.state = "vulnerable"
                self.timer = 120
                self.data = {}

        elif self.state == "vulnerable":
            self.timer -= 1
            if self.timer <= 0:
                self.state = "idle"
                self.timer = 20 if not self.phase2 else 12

        for pt in self.hit_particles:
            pt["x"] += pt["vx"]; pt["y"] += pt["vy"]; pt["life"] -= 1
        self.hit_particles = [pt for pt in self.hit_particles if pt["life"] > 0]

        # Blue eye flame particles (phase 2)
        if self.phase2:
            self.eye_anim_t += 1
            ex = self.x - self.size // 2 + self.size * 0.60
            ey = self.y - self.size // 2 + self.size * 0.30
            if self.eye_anim_t % 2 == 0:
                for _ in range(2):
                    a = random.uniform(-math.pi * 0.85, -math.pi * 0.15)
                    spd = random.uniform(0.8, 2.5)
                    self.eye_particles.append({
                        "x": float(ex + random.uniform(-5, 5)),
                        "y": float(ey + random.uniform(-3, 3)),
                        "vx": math.cos(a) * spd * 0.25,
                        "vy": math.sin(a) * spd,
                        "life": random.randint(10, 22),
                        "max_life": 22,
                    })
            for ep in self.eye_particles:
                ep["x"] += ep["vx"]; ep["y"] += ep["vy"]; ep["life"] -= 1
            self.eye_particles = [ep for ep in self.eye_particles if ep["life"] > 0]

    # ── helpers ──

    def _fire_blasters(self, player, blasters):
        for b in blasters:
            if not b.get("alive", True): continue
            if b.get("delay", 0) > 0:
                b["delay"] -= 1
                continue
            if b.get("charge_t", 0) > 0:
                b["charge_t"] -= 1
                continue
            b.setdefault("beam_t", 20)
            b["beam_t"] -= 1
            aim = b["aim"]
            bx, by = b["x"], b["y"]
            beam_len = 650
            dx2, dy2 = player.x - bx, player.y - by
            t = max(0.0, min(1.0, (dx2 * math.cos(aim) + dy2 * math.sin(aim)) / beam_len))
            cpx = bx + math.cos(aim) * t * beam_len
            cpy = by + math.sin(aim) * t * beam_len
            if math.hypot(player.x - cpx, player.y - cpy) < 26:
                player.take_damage(2)
            if b["beam_t"] <= 0:
                b["alive"] = False

    def _do_first_turn(self, player):
        d = self.data
        d["sub_timer"] -= 1
        sub = d["sub_phase"]

        if sub == "gravity":
            sd = d["gravity_dir"]
            f = 15.0
            if sd == "left":   player.knockback_vx = -f
            elif sd == "right": player.knockback_vx = f
            elif sd == "up":    player.knockback_vy = -f
            elif sd == "down":  player.knockback_vy = f
            if d["sub_timer"] <= 0:
                n = 7
                if sd in ("left", "right"):
                    d["spikes_pos"] = [int(HEIGHT / n * (i + 0.5)) for i in range(n)]
                else:
                    d["spikes_pos"] = [int(WIDTH / n * (i + 0.5)) for i in range(n)]
                d["spike_wall"] = sd
                d["sub_phase"] = "spike_delay"; d["sub_timer"] = 48  # 0.8초 대기

        elif sub == "spike_delay":
            d["sub_timer"] -= 1
            if d["sub_timer"] <= 0:
                d["sub_phase"] = "floor_spikes"; d["sub_timer"] = 40

        elif sub == "floor_spikes":
            wall = d["spike_wall"]
            near = ((wall == "left" and player.x < 60) or
                    (wall == "right" and player.x > WIDTH - 60) or
                    (wall == "up" and player.y < 60) or
                    (wall == "down" and player.y > HEIGHT - 60))
            if near:
                player.take_damage(2)
            if d["sub_timer"] <= 0:
                cx3 = int(self.x)
                r3 = 150
                d["blasters"] = [
                    {"x": float(cx3 + r3 * math.cos(a)),
                     "y": float(HEIGHT // 2 + r3 * math.sin(a)),
                     "aim": a + math.pi,
                     "charge_t": 22, "delay": i * 20, "alive": True}
                    for i, a in enumerate([0, math.pi / 2, math.pi, 3 * math.pi / 2])
                ]
                d["sub_phase"] = "blasters"; d["sub_timer"] = 90

        elif sub == "blasters":
            self._fire_blasters(player, d["blasters"])
            if d["sub_timer"] <= 0:
                d["wall_x"] = float(WIDTH + 20)
                d["sub_phase"] = "bone_wall"; d["sub_timer"] = 65

        elif sub == "bone_wall":
            d["wall_x"] -= 3.2
            wx = d["wall_x"]; gy = d["gap_y"]; gh = 80
            tr = pygame.Rect(int(wx) - 12, 0, 24, max(0, gy - gh // 2))
            br = pygame.Rect(int(wx) - 12, gy + gh // 2, 24, max(0, HEIGHT - (gy + gh // 2)))
            if tr.colliderect(player.get_rect()) or br.colliderect(player.get_rect()):
                player.take_damage(2)
            if wx < -20 or d["sub_timer"] <= 0:
                self.timer = 0

    def _do_bones_wave(self, player, ptype):
        d = self.data
        is_short = (ptype == "short_bone")
        max_c = 10 if is_short else 7
        interval = 28 if is_short else 42
        bh = 14 if is_short else 20
        spd = 5.5 if is_short else 4.0
        bw = 900

        d["spawn_timer"] -= 1
        if d["spawn_timer"] <= 0 and d["spawn_count"] < max_c:
            fr = (d["spawn_count"] % 2 == 0)
            yp = random.randint(70, HEIGHT - 70)
            d["bones"].append({
                "y": float(yp), "h": bh, "w": bw,
                "x": float(WIDTH) if fr else float(-bw),
                "speed": -spd if fr else spd,
                "blue": False, "alive": True,
            })
            d["spawn_count"] += 1
            d["spawn_timer"] = interval

        for b in d["bones"]:
            if not b["alive"]: continue
            b["x"] += b["speed"]
            br = pygame.Rect(int(b["x"]), int(b["y"]) - b["h"] // 2, int(b["w"]), b["h"])
            if br.colliderect(player.get_rect()):
                player.take_damage(1)
            if b["speed"] < 0 and b["x"] + b["w"] < 0:
                b["alive"] = False
            elif b["speed"] > 0 and b["x"] > WIDTH + 20:
                b["alive"] = False
        d["bones"] = [b for b in d["bones"] if b["alive"]]
        if d["spawn_count"] >= max_c and not d["bones"]:
            self.timer = 0

    def _do_blue_white(self, player):
        d = self.data
        if "prev_px" not in d:
            d["prev_px"], d["prev_py"] = player.x, player.y
        moving = abs(player.x - d["prev_px"]) > 0.5 or abs(player.y - d["prev_py"]) > 0.5
        d["prev_px"], d["prev_py"] = player.x, player.y

        max_c = 8; bw = 900; bh = 20
        d["spawn_timer"] -= 1
        if d["spawn_timer"] <= 0 and d["spawn_count"] < max_c:
            fr = (d["spawn_count"] % 2 == 0)
            yp = random.randint(70, HEIGHT - 70)
            d["bones"].append({
                "y": float(yp), "h": bh, "w": bw,
                "x": float(WIDTH) if fr else float(-bw),
                "speed": -4.5 if fr else 4.5,
                "blue": random.random() < 0.5, "alive": True,
            })
            d["spawn_count"] += 1
            d["spawn_timer"] = 38

        for b in d["bones"]:
            if not b["alive"]: continue
            b["x"] += b["speed"]
            br = pygame.Rect(int(b["x"]), int(b["y"]) - b["h"] // 2, int(b["w"]), b["h"])
            if br.colliderect(player.get_rect()):
                if not b["blue"] or moving:
                    player.take_damage(1)
            if b["speed"] < 0 and b["x"] + b["w"] < 0:
                b["alive"] = False
            elif b["speed"] > 0 and b["x"] > WIDTH + 20:
                b["alive"] = False
        d["bones"] = [b for b in d["bones"] if b["alive"]]
        if d["spawn_count"] >= max_c and not d["bones"]:
            self.timer = 0

    def _do_slams(self, player, ptype):
        d = self.data
        pull = 14.0 if ptype == "slam_gravity" else 19.0
        pull_dur = 22 if ptype == "slam_gravity" else 13
        spike_lf = 30 if ptype == "slam_gravity" else 20
        wait_t = 22 if ptype == "slam_gravity" else 13

        for sp in d["spikes"]:
            sp["life"] -= 1
            wall = sp["wall"]
            if ((wall == "left" and player.x < 60) or (wall == "right" and player.x > WIDTH - 60) or
                    (wall == "up" and player.y < 60) or (wall == "down" and player.y > HEIGHT - 60)):
                player.take_damage(1)
        d["spikes"] = [sp for sp in d["spikes"] if sp["life"] > 0]

        if d["slam_count"] >= d["max_slams"]:
            if not d["spikes"]: self.timer = 0
            return

        if d["slam_phase"] == "waiting":
            d["slam_dir"] = random.choice(["left", "right", "up", "down"])
            d["slam_timer"] = pull_dur
            d["slam_phase"] = "pulling"
        elif d["slam_phase"] == "pulling":
            sd = d["slam_dir"]
            if sd == "left":   player.knockback_vx = -pull
            elif sd == "right": player.knockback_vx = pull
            elif sd == "up":    player.knockback_vy = -pull
            elif sd == "down":  player.knockback_vy = pull
            d["slam_timer"] -= 1
            if d["slam_timer"] <= 0:
                d["slam_phase"] = "spike_delay"
                d["slam_timer"] = 48  # 0.8초 대기
        elif d["slam_phase"] == "spike_delay":
            d["slam_timer"] -= 1
            if d["slam_timer"] <= 0:
                d["spikes"].append({"wall": d["slam_dir"], "life": spike_lf})
                d["slam_count"] += 1
                d["slam_phase"] = "spike_wait"
                d["slam_timer"] = wait_t
        elif d["slam_phase"] == "spike_wait":
            d["slam_timer"] -= 1
            if d["slam_timer"] <= 0 and d["slam_count"] < d["max_slams"]:
                d["slam_phase"] = "waiting"

    def _do_platforms(self, player):
        d = self.data
        d["spike_y"] = max(d["spike_y"] - 0.6, float(HEIGHT * 0.55))
        for pl in d["platforms"]:
            pl["x"] += pl["vx"]
            if pl["x"] < 60 or pl["x"] > WIDTH * 0.58:
                pl["vx"] *= -1
        on_pl = any(
            pygame.Rect(int(pl["x"]) - d["pw"] // 2, int(pl["y"]) - d["ph"] // 2,
                        d["pw"], d["ph"]).colliderect(player.get_rect())
            for pl in d["platforms"]
        )
        if player.y > d["spike_y"] and not on_pl:
            player.take_damage(1)
        if d["spike_y"] <= HEIGHT * 0.55 + 1:
            self.timer = max(0, self.timer - 2)

    def _do_fast_blasters(self, player):
        d = self.data
        d["spawn_timer"] -= 1
        if d["spawn_timer"] <= 0 and d["total_spawned"] < d["max_blasters"]:
            bx4 = float(random.randint(50, WIDTH // 2 - 40))
            by4 = float(random.randint(60, HEIGHT - 60))
            aim4 = math.atan2(player.y - by4, player.x - bx4)
            d["blasters"].append({
                "x": bx4, "y": by4, "aim": aim4,
                "charge_t": 15, "delay": 0, "alive": True,
            })
            d["total_spawned"] += 1
            d["spawn_timer"] = 25 if not self.phase2 else 17
        self._fire_blasters(player, d["blasters"])
        if d["total_spawned"] >= d["max_blasters"] and all(not b["alive"] for b in d["blasters"]):
            self.timer = 0

    def _do_rotating(self, player):
        d = self.data
        d["orbit_angle"] += d["angular_speed"]
        cx4, cy4, r4 = d["cx"], d["cy"], d["orbit_r"]
        for bl in d["blasters"]:
            angle = d["orbit_angle"] + bl["offset"]
            bl["bx"] = cx4 + r4 * math.cos(angle)
            bl["by"] = cy4 + r4 * math.sin(angle)
            bl["aim"] = angle + math.pi
            if bl["fire_cd"] > 0:
                bl["fire_cd"] -= 1
            else:
                bl.setdefault("beam_t", 18)
                bl["beam_t"] -= 1
                aim5 = bl["aim"]
                bx5, by5 = bl["bx"], bl["by"]
                beam_len = 500
                dx5, dy5 = player.x - bx5, player.y - by5
                t5 = max(0.0, min(1.0, (dx5 * math.cos(aim5) + dy5 * math.sin(aim5)) / beam_len))
                cpx2 = bx5 + math.cos(aim5) * t5 * beam_len
                cpy2 = by5 + math.sin(aim5) * t5 * beam_len
                if math.hypot(player.x - cpx2, player.y - cpy2) < 26:
                    player.take_damage(2)
                if bl["beam_t"] <= 0:
                    bl["fire_cd"] = 55
                    del bl["beam_t"]

    def _do_bone_gap(self, player):
        d = self.data
        spd = 5.5 if not self.phase2 else 7.5
        d["spawn_timer"] -= 1
        if d["spawn_timer"] <= 0 and d["spawn_count"] < d["max_walls"]:
            d["walls"].append({
                "x": float(WIDTH + 20),
                "gap_y": random.randint(90, HEIGHT - 90),
                "gap_h": 80 if not self.phase2 else 65,
                "speed": spd, "alive": True,
            })
            d["spawn_count"] += 1
            d["spawn_timer"] = 52
        for w in d["walls"]:
            if not w["alive"]: continue
            w["x"] -= w["speed"]
            wx5, gy5, gh5 = int(w["x"]), w["gap_y"], w["gap_h"]
            tr2 = pygame.Rect(wx5 - 12, 0, 24, max(0, gy5 - gh5 // 2))
            br2 = pygame.Rect(wx5 - 12, gy5 + gh5 // 2, 24, max(0, HEIGHT - (gy5 + gh5 // 2)))
            if tr2.colliderect(player.get_rect()) or br2.colliderect(player.get_rect()):
                player.take_damage(2)
            if wx5 < -20: w["alive"] = False
        d["walls"] = [w for w in d["walls"] if w["alive"]]
        if d["spawn_count"] >= d["max_walls"] and not d["walls"]:
            self.timer = 0

    def _do_final(self, player):
        d = self.data
        d["sub_timer"] -= 1
        sub = d["sub_phase"]

        if sub == "bone_tunnel":
            d["spawn_timer"] -= 1
            if d["spawn_timer"] <= 0:
                yp2 = random.choice([random.randint(15, HEIGHT // 3 - 10),
                                     random.randint(2 * HEIGHT // 3 + 10, HEIGHT - 15)])
                d["bones"].append({
                    "y": float(yp2), "h": 22, "w": 900,
                    "x": float(WIDTH + 40), "speed": -13.0,
                    "blue": False, "alive": True,
                })
                d["spawn_timer"] = 7
            for b in d["bones"]:
                if not b["alive"]: continue
                b["x"] += b["speed"]
                br3 = pygame.Rect(int(b["x"]), int(b["y"]) - b["h"] // 2, int(b["w"]), b["h"])
                if br3.colliderect(player.get_rect()):
                    player.take_damage(2)
                if b["x"] + b["w"] < -20: b["alive"] = False
            d["bones"] = [b for b in d["bones"] if b["alive"]]
            if d["sub_timer"] <= 0:
                d["sub_phase"] = "blaster_spam"; d["sub_timer"] = 95
                d["blasters"] = []; d["spawn_timer"] = 0

        elif sub == "blaster_spam":
            d["spawn_timer"] -= 1
            active_bl = [b for b in d["blasters"] if b.get("alive", False)]
            if d["spawn_timer"] <= 0 and len(active_bl) < 5:
                bx6 = float(random.randint(40, WIDTH // 2 - 30))
                by6 = float(random.randint(40, HEIGHT - 40))
                aim6 = math.atan2(player.y - by6, player.x - bx6)
                d["blasters"].append({"x": bx6, "y": by6, "aim": aim6,
                                      "charge_t": 12, "delay": 0, "alive": True})
                d["spawn_timer"] = 11
            self._fire_blasters(player, d["blasters"])
            d["blasters"] = [b for b in d["blasters"] if b.get("alive", False)]
            if d["sub_timer"] <= 0:
                d["sub_phase"] = "slam_frenzy"; d["sub_timer"] = 115
                d.update({"slams_done": 0, "slam_phase": "waiting",
                           "slam_timer": 0, "slam_dir": None, "spikes": []})

        elif sub == "slam_frenzy":
            for sp in d["spikes"]:
                sp["life"] -= 1
                wall = sp["wall"]
                if ((wall == "left" and player.x < 60) or (wall == "right" and player.x > WIDTH - 60) or
                        (wall == "up" and player.y < 60) or (wall == "down" and player.y > HEIGHT - 60)):
                    player.take_damage(2)
            d["spikes"] = [sp for sp in d["spikes"] if sp["life"] > 0]
            if d["slams_done"] < 8:
                if d["slam_phase"] == "waiting":
                    d["slam_dir"] = random.choice(["left", "right", "up", "down"])
                    d["slam_timer"] = 11; d["slam_phase"] = "pulling"
                elif d["slam_phase"] == "pulling":
                    sd2 = d["slam_dir"]
                    if sd2 == "left":   player.knockback_vx = -21.0
                    elif sd2 == "right": player.knockback_vx = 21.0
                    elif sd2 == "up":    player.knockback_vy = -21.0
                    elif sd2 == "down":  player.knockback_vy = 21.0
                    d["slam_timer"] -= 1
                    if d["slam_timer"] <= 0:
                        d["slam_phase"] = "spike_delay2"; d["slam_timer"] = 48
                elif d["slam_phase"] == "spike_delay2":
                    d["slam_timer"] -= 1
                    if d["slam_timer"] <= 0:
                        d["spikes"].append({"wall": d["slam_dir"], "life": 18})
                        d["slams_done"] += 1; d["slam_phase"] = "waiting"
            if d["sub_timer"] <= 0 and not d["spikes"]:
                self.timer = 0

    def take_damage(self, amount):
        if not self.is_vulnerable(): return
        self.hp -= amount
        for _ in range(8):
            a = random.uniform(0, 2 * math.pi)
            spd = random.uniform(2, 6)
            self.hit_particles.append({
                "x": float(self.x), "y": float(self.y),
                "vx": math.cos(a) * spd, "vy": math.sin(a) * spd,
                "life": random.randint(12, 22), "max_life": 22,
            })

    def _draw_blaster(self, bx, by, aim, charge_t, beam_t):
        ibx, iby = int(bx), int(by)
        glow = int(20 + max(0, (28 - charge_t)) * 1.2) if charge_t > 0 else 20
        pygame.draw.circle(screen, (220, 220, 255), (ibx, iby), glow)
        pygame.draw.circle(screen, BLACK, (ibx, iby), 10)
        ex = ibx + int(math.cos(aim) * 9)
        ey = iby + int(math.sin(aim) * 9)
        pygame.draw.circle(screen, (0, 210, 255), (ex, ey), 6)
        if beam_t > 0:
            beam_len = 650
            ex2 = int(bx + math.cos(aim) * beam_len)
            ey2 = int(by + math.sin(aim) * beam_len)
            bw = max(2, int(beam_t * 0.55))
            pygame.draw.line(screen, (80, 255, 255), (ibx, iby), (ex2, ey2), bw + 5)
            pygame.draw.line(screen, WHITE, (ibx, iby), (ex2, ey2), bw)

    def draw(self, small_font):
        # Draw blasters (behind sprite)
        if self.pattern in ("blaster_circle", "fast_blasters", "first_turn"):
            for b in self.data.get("blasters", []):
                if not b.get("alive", True): continue
                self._draw_blaster(b["x"], b["y"], b["aim"],
                                   b.get("charge_t", 0), b.get("beam_t", 0))
        if self.pattern == "rotating_blasters" and self.state == "active":
            for bl in self.data.get("blasters", []):
                self._draw_blaster(bl.get("bx", 0), bl.get("by", 0), bl.get("aim", 0),
                                   0, bl.get("beam_t", 0))
        if self.pattern == "final_overdrive":
            for b in self.data.get("blasters", []):
                if not b.get("alive", True): continue
                self._draw_blaster(b["x"], b["y"], b["aim"],
                                   b.get("charge_t", 0), b.get("beam_t", 0))

        # Sans sprite
        sprite = pygame.transform.scale(SANS_IMAGE, (self.size, self.size))
        if self.is_vulnerable():
            tinted = sprite.copy()
            tinted.fill((255, 230, 80, 0), special_flags=pygame.BLEND_RGBA_ADD)
            sprite = tinted
        sx = int(self.x) - self.size // 2
        sy = int(self.y) - self.size // 2
        screen.blit(sprite, (sx, sy))

        # Phase 2: blue eye flame
        if self.phase2:
            eye_gx = sx + int(self.size * 0.60)
            eye_gy = sy + int(self.size * 0.30)
            # Yellow eye base
            glow_s = pygame.Surface((26, 26), pygame.SRCALPHA)
            pygame.draw.circle(glow_s, (255, 220, 0, 90), (13, 13), 13)
            screen.blit(glow_s, (eye_gx - 13, eye_gy - 13))
            pygame.draw.circle(screen, YELLOW, (eye_gx, eye_gy), 5)
            pygame.draw.circle(screen, WHITE, (eye_gx, eye_gy), 2)
            # Blue flame particles
            for ep in self.eye_particles:
                ratio = max(0.0, ep["life"] / ep["max_life"])
                r = max(1, int(8 * ratio))
                b_val = int(180 + 75 * ratio)
                g_val = int(130 * ratio)
                fs = pygame.Surface((r * 2 + 1, r * 2 + 1), pygame.SRCALPHA)
                pygame.draw.circle(fs, (int(20 * ratio), g_val, b_val, int(210 * ratio)),
                                   (r, r), r)
                screen.blit(fs, (int(ep["x"]) - r, int(ep["y"]) - r))

        # Bones (detailed shape)
        def _draw_bone(bx, by_center, bw, bh, col, border):
            cy = by_center
            shaft_h = max(4, bh - 8)
            # shaft
            pygame.draw.rect(screen, col,
                             pygame.Rect(int(bx), int(cy - shaft_h // 2), int(bw), shaft_h))
            # left knob: two overlapping circles
            kr = bh // 2 + 2
            lx = int(bx) + kr // 2
            pygame.draw.circle(screen, col, (lx, int(cy - bh // 4)), kr)
            pygame.draw.circle(screen, col, (lx, int(cy + bh // 4)), kr)
            # right knob
            rx = int(bx + bw) - kr // 2
            pygame.draw.circle(screen, col, (rx, int(cy - bh // 4)), kr)
            pygame.draw.circle(screen, col, (rx, int(cy + bh // 4)), kr)
            # outline shaft
            pygame.draw.rect(screen, border,
                             pygame.Rect(int(bx), int(cy - shaft_h // 2), int(bw), shaft_h), 2)

        for b in self.data.get("bones", []):
            if not b.get("alive", True): continue
            col = (80, 130, 255) if b.get("blue") else WHITE
            border = (160, 200, 255) if b.get("blue") else (200, 200, 200)
            _draw_bone(b["x"], b["y"], b["w"], b["h"], col, border)

        # Bone gap walls
        for w in self.data.get("walls", []):
            if not w.get("alive", True): continue
            wx6, gy6, gh6 = int(w["x"]), w["gap_y"], w["gap_h"]
            tr3 = pygame.Rect(wx6 - 12, 0, 24, max(0, gy6 - gh6 // 2))
            br4 = pygame.Rect(wx6 - 12, gy6 + gh6 // 2, 24, max(0, HEIGHT - (gy6 + gh6 // 2)))
            pygame.draw.rect(screen, WHITE, tr3); pygame.draw.rect(screen, WHITE, br4)
            pygame.draw.rect(screen, (180, 180, 180), tr3, 2)
            pygame.draw.rect(screen, (180, 180, 180), br4, 2)

        # First turn: bone wall
        if self.pattern == "first_turn" and self.data.get("sub_phase") == "bone_wall":
            wx7, gy7 = int(self.data["wall_x"]), self.data["gap_y"]
            gh7 = 80
            tr4 = pygame.Rect(wx7 - 12, 0, 24, max(0, gy7 - gh7 // 2))
            br5 = pygame.Rect(wx7 - 12, gy7 + gh7 // 2, 24, max(0, HEIGHT - (gy7 + gh7 // 2)))
            pygame.draw.rect(screen, WHITE, tr4); pygame.draw.rect(screen, WHITE, br5)

        # Slam / first_turn spikes
        def draw_spikes_at_wall(wall):
            n = 6; col_sp = (220, 220, 255)
            if wall == "left":
                for i in range(n):
                    ysp = int(HEIGHT / n * (i + 0.5))
                    pygame.draw.polygon(screen, col_sp, [(0, ysp - 14), (0, ysp + 14), (36, ysp)])
            elif wall == "right":
                for i in range(n):
                    ysp = int(HEIGHT / n * (i + 0.5))
                    pygame.draw.polygon(screen, col_sp, [(WIDTH, ysp - 14), (WIDTH, ysp + 14), (WIDTH - 36, ysp)])
            elif wall == "up":
                for i in range(n):
                    xsp = int(WIDTH / n * (i + 0.5))
                    pygame.draw.polygon(screen, col_sp, [(xsp - 14, 0), (xsp + 14, 0), (xsp, 36)])
            elif wall == "down":
                for i in range(n):
                    xsp = int(WIDTH / n * (i + 0.5))
                    pygame.draw.polygon(screen, col_sp, [(xsp - 14, HEIGHT), (xsp + 14, HEIGHT), (xsp, HEIGHT - 36)])

        if self.pattern == "first_turn" and self.data.get("sub_phase") == "floor_spikes":
            draw_spikes_at_wall(self.data.get("spike_wall"))
        for sp in self.data.get("spikes", []):
            draw_spikes_at_wall(sp["wall"])

        # Bone platforms
        if self.pattern == "bone_platforms" and self.state == "active":
            d8 = self.data
            sy = d8["spike_y"]
            if sy < HEIGHT:
                ssurf = pygame.Surface((WIDTH, max(1, int(HEIGHT - sy))), pygame.SRCALPHA)
                ssurf.fill((200, 200, 255, 60))
                screen.blit(ssurf, (0, int(sy)))
                pygame.draw.line(screen, (200, 200, 255), (0, int(sy)), (WIDTH, int(sy)), 2)
                n = 10; sw2 = WIDTH // n
                for i in range(n):
                    sxp2 = i * sw2 + sw2 // 2
                    pygame.draw.polygon(screen, WHITE,
                                        [(sxp2 - sw2 // 3, HEIGHT),
                                         (sxp2, int(sy) + 8),
                                         (sxp2 + sw2 // 3, HEIGHT)])
            for pl in d8["platforms"]:
                pygame.draw.rect(screen, WHITE,
                                 pygame.Rect(int(pl["x"]) - d8["pw"] // 2,
                                             int(pl["y"]) - d8["ph"] // 2,
                                             d8["pw"], d8["ph"]))

        # Spare UI
        if self.pattern == "spare" and self.state == "active":
            ssurf2 = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            ssurf2.fill((0, 0, 0, 100))
            screen.blit(ssurf2, (0, 0))
            msgs = [
                "* ...",
                "* do you wanna have a bad time?",
                "* cuz if you keep going...",
                "* you're really not gonna like what happens next.",
                "",
                "ATTACK (SPACE) to continue  |  spare = instant death",
            ]
            for i, msg in enumerate(msgs):
                col_t = YELLOW if i == len(msgs) - 1 else WHITE
                ts = small_font.render(msg, True, col_t)
                screen.blit(ts, (WIDTH // 2 - ts.get_width() // 2, HEIGHT // 2 - 72 + i * 25))
            ratio = max(0, self.data["spare_timer"]) / 300
            bw2 = 200
            pygame.draw.rect(screen, (60, 60, 60), (WIDTH // 2 - bw2 // 2, HEIGHT // 2 + 82, bw2, 10))
            pygame.draw.rect(screen, YELLOW, (WIDTH // 2 - bw2 // 2, HEIGHT // 2 + 82, int(bw2 * ratio), 10))

        # HP bar
        bar_w = 220
        col_hp = (100, 100, 255) if not self.phase2 else (220, 80, 80)
        pygame.draw.rect(screen, (60, 60, 60), (WIDTH // 2 - bar_w // 2, 16, bar_w, 16))
        pygame.draw.rect(screen, col_hp,
                         (WIDTH // 2 - bar_w // 2, 16,
                          int(bar_w * max(self.hp, 0) / self.max_hp), 16))
        lbl = self.name + (" [PHASE 2]" if self.phase2 else "")
        nt = small_font.render(lbl, True, WHITE)
        screen.blit(nt, (WIDTH // 2 - nt.get_width() // 2, 34))

        for pt in self.hit_particles:
            ratio2 = pt["life"] / pt["max_life"]
            pygame.draw.circle(screen, (int(100 * ratio2), int(100 * ratio2), int(255 * ratio2)),
                               (int(pt["x"]), int(pt["y"])), max(1, int(5 * ratio2)))


# ═══════════════════════════════════════════════════════════════════
#  ASRIEL BOSS (숨겨진 진 최종 보스)
# ═══════════════════════════════════════════════════════════════════
class AsrielBoss:
    """아스리엘. 1페이즈(전능의 신)는 일반 보스전처럼 대시로 때려 체력을 깎고,
    2페이즈(절대신)는 무적 상태가 되어 탄막을 뚫고 SAVE(대시)로 마무리한다."""

    name = "ASRIEL"

    PHASE1_SEQ = [
        "chaos_saber", "chaos_buster", "shocker_breaker",
        "star_blaster", "hyper_goner",
    ]
    PHASE2_SEQ = ["angels_ray", "endless_comet", "final_beam"]

    PATTERN_QUOTE = {
        "chaos_saber":     "* Chaos Saber! Try to keep up!",
        "chaos_buster":    "* Chaos Buster!",
        "shocker_breaker": "* Shocker Breaker! Feel the wrath of a god!",
        "star_blaster":    "* Star Blaster! I'll bring down the galaxy itself!",
        "hyper_goner":     "* This ends here... Hyper Goner!!",
        "angels_ray":      "* Angel's Ray... resistance is futile.",
        "endless_comet":   "* Endless Comet! The sky itself is falling!",
        "final_beam":      "* ...this is the end.",
        "save_window":     "* ...will you save me?",
    }

    def __init__(self):
        self.x = float(WIDTH * 0.74)
        self.y = float(HEIGHT // 2)
        self.size = 120
        self.hp = 150
        self.max_hp = 150
        self.state = "idle"
        self.timer = 50
        self.pattern = None
        self.data = {}
        self.turn = 0
        self.phase2 = False
        self.phase2_turns = 0
        self.saved = False
        self.hit_particles = []
        self.quote_timer = 0
        self.anim_t = 0

    def get_rect(self):
        return pygame.Rect(int(self.x) - self.size // 2, int(self.y) - self.size // 2,
                           self.size, self.size)

    def is_vulnerable(self):
        return (not self.phase2) and self.state == "vulnerable"

    def start_pattern(self):
        if not self.phase2:
            self.pattern = self.PHASE1_SEQ[self.turn % len(self.PHASE1_SEQ)]
            self.turn += 1
        else:
            cycle_pos = self.phase2_turns % 4
            if cycle_pos == 3:
                self.pattern = "save_window"
            else:
                self.pattern = self.PHASE2_SEQ[cycle_pos]
            self.phase2_turns += 1

        self.state = "telegraph"
        self.data = {}
        self.quote_timer = 80

        tele = {
            "chaos_saber": 30, "chaos_buster": 30, "shocker_breaker": 25,
            "star_blaster": 28, "hyper_goner": 35,
            "angels_ray": 30, "endless_comet": 25, "final_beam": 40,
            "save_window": 40,
        }
        act = {
            "chaos_saber": 260, "chaos_buster": 320, "shocker_breaker": 260,
            "star_blaster": 260, "hyper_goner": 340,
            "angels_ray": 280, "endless_comet": 280, "final_beam": 210,
            "save_window": 260,
        }
        self.timer = tele.get(self.pattern, 28)
        self.data["_act"] = act.get(self.pattern, 240)

        if self.pattern == "chaos_saber":
            self.data.update({"waves": [], "spawn_timer": 0, "wave_count": 0})
        elif self.pattern == "chaos_buster":
            self.data.update({"stars": [], "spawn_timer": 0, "spawn_count": 0,
                               "sub_phase": "stars", "sub_timer": 0, "beam_gap": None})
        elif self.pattern == "shocker_breaker":
            self.data.update({"zones": [], "spawn_timer": 0, "spawn_count": 0})
        elif self.pattern == "star_blaster":
            self.data.update({"big_stars": [], "frags": [], "spawn_timer": 0, "spawn_count": 0})
        elif self.pattern == "hyper_goner":
            self.data.update({"frags": [], "spawn_timer": 0,
                               "pull_x": float(WIDTH // 2), "pull_y": float(HEIGHT // 2)})
        elif self.pattern == "angels_ray":
            self.data.update({"rays": [], "spawn_timer": 0, "spawn_count": 0})
        elif self.pattern == "endless_comet":
            self.data.update({"comets": [], "spawn_timer": 0, "spawn_count": 0})
        elif self.pattern == "final_beam":
            self.data.update({"sub_phase": "warn", "sub_timer": 60,
                               "gap_side": random.choice(["top", "bottom"]), "gap_h": 60})
        elif self.pattern == "save_window":
            self.data.update({})

    def update(self, player):
        tx, ty = float(WIDTH * 0.74), float(HEIGHT // 2)
        self.x += (tx - self.x) * 0.015
        self.y += (ty - self.y) * 0.015
        self.anim_t += 1

        if self.quote_timer > 0:
            self.quote_timer -= 1

        if self.state == "idle":
            self.timer -= 1
            if self.timer <= 0:
                self.start_pattern()

        elif self.state == "telegraph":
            self.timer -= 1
            if self.timer <= 0:
                self.state = "active"
                self.timer = self.data.pop("_act", 240)

        elif self.state == "active":
            self.timer -= 1
            p = self.pattern
            if   p == "chaos_saber":     self._do_chaos_saber(player)
            elif p == "chaos_buster":    self._do_chaos_buster(player)
            elif p == "shocker_breaker": self._do_shocker_breaker(player)
            elif p == "star_blaster":    self._do_star_blaster(player)
            elif p == "hyper_goner":     self._do_hyper_goner(player)
            elif p == "angels_ray":      self._do_angels_ray(player)
            elif p == "endless_comet":   self._do_endless_comet(player)
            elif p == "final_beam":      self._do_final_beam(player)
            # save_window: 판정은 전투 루프에서 대시 충돌로 직접 처리한다.

            if self.timer <= 0:
                if p == "save_window":
                    # 구원 기회를 놓쳤다 - 다시 탄막 공세로.
                    self.state = "idle"
                    self.timer = 30
                elif not self.phase2:
                    self.state = "vulnerable"
                    self.timer = 120
                else:
                    self.state = "idle"
                    self.timer = 30
                self.data = {}

        elif self.state == "vulnerable":
            self.timer -= 1
            if self.timer <= 0:
                self.state = "idle"
                self.timer = 25

        for pt in self.hit_particles:
            pt["x"] += pt["vx"]; pt["y"] += pt["vy"]; pt["life"] -= 1
        self.hit_particles = [pt for pt in self.hit_particles if pt["life"] > 0]

    # ── 1페이즈 패턴 ─────────────────────────────────────────────

    def _do_chaos_saber(self, player):
        d = self.data
        d["spawn_timer"] -= 1
        if d["spawn_timer"] <= 0 and d["wave_count"] < 5:
            d["wave_count"] += 1
            gap1 = random.randint(40, HEIGHT // 2 - 40)
            gap2 = random.randint(HEIGHT // 2 + 40, HEIGHT - 40)
            d["waves"].append({"x": float(WIDTH + 30), "gap1": gap1, "gap2": gap2,
                                "gap_h": 70, "alive": True})
            d["spawn_timer"] = 42
        for w in d["waves"]:
            if not w["alive"]:
                continue
            w["x"] -= 5.2
            if w["x"] < -30:
                w["alive"] = False
                continue
            if abs(player.x - w["x"]) < 16:
                in_gap1 = abs(player.y - w["gap1"]) < w["gap_h"] // 2
                in_gap2 = abs(player.y - w["gap2"]) < w["gap_h"] // 2
                if not (in_gap1 or in_gap2):
                    player.take_damage(1)
        d["waves"] = [w for w in d["waves"] if w["alive"]]
        if d["wave_count"] >= 5 and not d["waves"]:
            self.timer = 0

    def _do_chaos_buster(self, player):
        d = self.data
        if d["sub_phase"] == "stars":
            d["spawn_timer"] -= 1
            if d["spawn_timer"] <= 0 and d["spawn_count"] < 16:
                d["spawn_count"] += 1
                angle = math.atan2(player.y - self.y, player.x - self.x) + random.uniform(-0.3, 0.3)
                spd = random.uniform(4.5, 6.5)
                d["stars"].append({"x": float(self.x), "y": float(self.y),
                                    "vx": math.cos(angle) * spd, "vy": math.sin(angle) * spd,
                                    "alive": True})
                d["spawn_timer"] = 10
            for s in d["stars"]:
                if not s["alive"]:
                    continue
                s["x"] += s["vx"]; s["y"] += s["vy"]
                if s["x"] < -40 or s["x"] > WIDTH + 40 or s["y"] < -40 or s["y"] > HEIGHT + 40:
                    s["alive"] = False
                    continue
                if math.hypot(s["x"] - player.x, s["y"] - player.y) < 16 + player.size * 0.45:
                    player.take_damage(1); s["alive"] = False
            d["stars"] = [s for s in d["stars"] if s["alive"]]
            if d["spawn_count"] >= 16 and not d["stars"]:
                d["sub_phase"] = "beam_warn"
                d["sub_timer"] = 55
                d["beam_gap"] = random.choice(["top", "bottom"])
        elif d["sub_phase"] == "beam_warn":
            d["sub_timer"] -= 1
            if d["sub_timer"] <= 0:
                d["sub_phase"] = "beam"
                d["sub_timer"] = 45
        elif d["sub_phase"] == "beam":
            d["sub_timer"] -= 1
            gap_h = 90
            if d["beam_gap"] == "top":
                safe_top, safe_bot = 0, gap_h
            else:
                safe_top, safe_bot = HEIGHT - gap_h, HEIGHT
            if not (safe_top <= player.y <= safe_bot):
                player.take_damage(1)
            if d["sub_timer"] <= 0:
                self.timer = 0

    def _do_shocker_breaker(self, player):
        d = self.data
        cols = 5
        cw = WIDTH // cols
        d["spawn_timer"] -= 1
        if d["spawn_timer"] <= 0 and d["spawn_count"] < 5:
            d["spawn_count"] += 1
            occupied = {z["col"] for z in d["zones"] if z["alive"] and z["fuse"] > 0}
            avail = [c for c in range(cols) if c not in occupied]
            col = random.choice(avail) if avail else random.randint(0, cols - 1)
            d["zones"].append({"col": col, "x": col * cw, "w": cw,
                                "fuse": 45, "erupt": 0, "alive": True})
            d["spawn_timer"] = 24
        for z in d["zones"]:
            if not z["alive"]:
                continue
            if z["fuse"] > 0:
                z["fuse"] -= 1
            else:
                z["erupt"] += 1
                zr = pygame.Rect(z["x"], 0, z["w"], HEIGHT)
                if zr.colliderect(player.get_rect()):
                    player.take_damage(1)
                if z["erupt"] > 20:
                    z["alive"] = False
        d["zones"] = [z for z in d["zones"] if z["alive"]]
        if d["spawn_count"] >= 5 and not d["zones"]:
            self.timer = 0

    def _do_star_blaster(self, player):
        d = self.data
        ground_y = HEIGHT - 40
        d["spawn_timer"] -= 1
        if d["spawn_timer"] <= 0 and d["spawn_count"] < 5:
            d["spawn_count"] += 1
            bx = random.randint(60, WIDTH - 60)
            d["big_stars"].append({"x": float(bx), "y": float(-30), "vy": 6.0,
                                    "alive": True, "warn": 30})
            d["spawn_timer"] = 55
        for bs in d["big_stars"]:
            if not bs["alive"]:
                continue
            if bs["warn"] > 0:
                bs["warn"] -= 1
                continue
            bs["y"] += bs["vy"]
            if bs["y"] >= ground_y:
                bs["alive"] = False
                for k in range(8):
                    ang = k * (math.pi / 4) + random.uniform(-0.2, 0.2)
                    spd = random.uniform(3.0, 5.5)
                    d["frags"].append({"x": bs["x"], "y": ground_y,
                                        "vx": math.cos(ang) * spd,
                                        "vy": math.sin(ang) * spd * 0.6 - 2.0,
                                        "life": 55, "alive": True})
            elif math.hypot(bs["x"] - player.x, bs["y"] - player.y) < 20 + player.size * 0.45:
                player.take_damage(1); bs["alive"] = False
        d["big_stars"] = [b for b in d["big_stars"] if b["alive"]]
        for f in d["frags"]:
            if not f["alive"]:
                continue
            f["x"] += f["vx"]; f["y"] += f["vy"]; f["vy"] += 0.15; f["life"] -= 1
            if f["life"] <= 0 or f["x"] < -30 or f["x"] > WIDTH + 30 or f["y"] > HEIGHT + 30:
                f["alive"] = False
                continue
            if math.hypot(f["x"] - player.x, f["y"] - player.y) < 10 + player.size * 0.4:
                player.take_damage(1); f["alive"] = False
        d["frags"] = [f for f in d["frags"] if f["alive"]]
        if d["spawn_count"] >= 5 and not d["big_stars"] and not d["frags"]:
            self.timer = 0

    def _do_hyper_goner(self, player):
        d = self.data
        cx, cy = d["pull_x"], d["pull_y"]
        dx = cx - player.x; dy = cy - player.y
        dist = math.hypot(dx, dy)
        if dist > 1:
            pull = 3.2
            player.knockback_vx = dx / dist * pull
            player.knockback_vy = dy / dist * pull
        if dist < 34:
            player.take_damage(1)

        d["spawn_timer"] -= 1
        if d["spawn_timer"] <= 0:
            edge = random.randint(0, 3)
            if edge == 0:   fx, fy = random.uniform(0, WIDTH), -20.0
            elif edge == 1: fx, fy = WIDTH + 20.0, random.uniform(0, HEIGHT)
            elif edge == 2: fx, fy = random.uniform(0, WIDTH), HEIGHT + 20.0
            else:           fx, fy = -20.0, random.uniform(0, HEIGHT)
            ang = math.atan2(cy - fy, cx - fx) + random.uniform(-0.4, 0.4)
            spd = random.uniform(3.0, 4.5)
            d["frags"].append({"x": fx, "y": fy, "vx": math.cos(ang) * spd,
                                "vy": math.sin(ang) * spd, "alive": True})
            d["spawn_timer"] = 14

        for f in d["frags"]:
            if not f["alive"]:
                continue
            f["x"] += f["vx"]; f["y"] += f["vy"]
            if math.hypot(f["x"] - cx, f["y"] - cy) < 20:
                f["alive"] = False
                continue
            if math.hypot(f["x"] - player.x, f["y"] - player.y) < 10 + player.size * 0.4:
                player.take_damage(1); f["alive"] = False
        d["frags"] = [f for f in d["frags"] if f["alive"]]

    # ── 2페이즈 패턴 ─────────────────────────────────────────────

    def _do_angels_ray(self, player):
        d = self.data
        d["spawn_timer"] -= 1
        if d["spawn_timer"] <= 0 and d["spawn_count"] < 10:
            d["spawn_count"] += 1
            edge = random.randint(0, 3)
            if edge == 0:   fx, fy = random.uniform(0, WIDTH), -20.0
            elif edge == 1: fx, fy = WIDTH + 20.0, random.uniform(0, HEIGHT)
            elif edge == 2: fx, fy = random.uniform(0, WIDTH), HEIGHT + 20.0
            else:           fx, fy = -20.0, random.uniform(0, HEIGHT)
            d["rays"].append({"x": fx, "y": fy, "vx": 0.0, "vy": 0.0, "alive": True, "age": 0})
            d["spawn_timer"] = 22
        for r in d["rays"]:
            if not r["alive"]:
                continue
            r["age"] += 1
            ddx = player.x - r["x"]; ddy = player.y - r["y"]
            dist = math.hypot(ddx, ddy) or 1
            turn = min(0.09, 0.02 + r["age"] * 0.0006)
            target_vx, target_vy = ddx / dist * 5.0, ddy / dist * 5.0
            r["vx"] += (target_vx - r["vx"]) * turn
            r["vy"] += (target_vy - r["vy"]) * turn
            r["x"] += r["vx"]; r["y"] += r["vy"]
            if r["x"] < -60 or r["x"] > WIDTH + 60 or r["y"] < -60 or r["y"] > HEIGHT + 60:
                r["alive"] = False
                continue
            if math.hypot(r["x"] - player.x, r["y"] - player.y) < 12 + player.size * 0.45:
                player.take_damage(1); r["alive"] = False
        d["rays"] = [r for r in d["rays"] if r["alive"]]
        if d["spawn_count"] >= 10 and not d["rays"]:
            self.timer = 0

    def _do_endless_comet(self, player):
        d = self.data
        d["spawn_timer"] -= 1
        if d["spawn_timer"] <= 0 and d["spawn_count"] < 40:
            n = min(3, 40 - d["spawn_count"])
            for _ in range(n):
                d["spawn_count"] += 1
                cx = random.uniform(20, WIDTH - 20)
                d["comets"].append({"x": cx, "y": -20.0, "vy": random.uniform(6.0, 8.0),
                                     "vx": random.uniform(-0.6, 0.6), "alive": True})
            d["spawn_timer"] = 9
        for c in d["comets"]:
            if not c["alive"]:
                continue
            c["x"] += c["vx"]; c["y"] += c["vy"]
            if c["y"] > HEIGHT + 30:
                c["alive"] = False
                continue
            if math.hypot(c["x"] - player.x, c["y"] - player.y) < 13 + player.size * 0.45:
                player.take_damage(1); c["alive"] = False
        d["comets"] = [c for c in d["comets"] if c["alive"]]
        if d["spawn_count"] >= 40 and not d["comets"]:
            self.timer = 0

    def _do_final_beam(self, player):
        d = self.data
        if d["sub_phase"] == "warn":
            d["sub_timer"] -= 1
            if d["sub_timer"] <= 0:
                d["sub_phase"] = "beam"
                d["sub_timer"] = 70
        else:
            d["sub_timer"] -= 1
            gap_h = d["gap_h"]
            if d["gap_side"] == "top":
                safe_top, safe_bot = 0, gap_h
            else:
                safe_top, safe_bot = HEIGHT - gap_h, HEIGHT
            if not (safe_top <= player.y <= safe_bot):
                player.take_damage(1)
            if d["sub_timer"] <= 0:
                self.timer = 0

    def take_damage(self, amount):
        if self.phase2 or self.state != "vulnerable":
            return
        self.hp -= amount
        for _ in range(10):
            a = random.uniform(0, 2 * math.pi); spd = random.uniform(2, 6)
            self.hit_particles.append({"x": float(self.x), "y": float(self.y),
                                        "vx": math.cos(a) * spd, "vy": math.sin(a) * spd,
                                        "life": random.randint(12, 22), "max_life": 22})
        if self.hp <= 0:
            self.hp = 0
            self.phase2 = True
            self.phase2_turns = 0
            self.state = "idle"
            self.timer = 70
            self.data = {}

    # ── 드로잉 헬퍼 ──────────────────────────────────────────────

    @staticmethod
    def _star_pts(cx, cy, r_out, r_in, spin, n=5):
        pts = []
        for k in range(n * 2):
            r = r_out if k % 2 == 0 else r_in
            a = spin + k * math.pi / n
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        return pts

    @classmethod
    def _draw_star(cls, surf, col, cx, cy, r_out, spin=0.0, core=WHITE, n=5):
        pygame.draw.polygon(surf, col, cls._star_pts(cx, cy, r_out, r_out * 0.42, spin, n))
        if core:
            pygame.draw.circle(surf, core, (int(cx), int(cy)), max(1, int(r_out * 0.3)))

    @staticmethod
    def _glow(surf, col, cx, cy, r, alpha=90):
        r = max(2, int(r))
        gs = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(gs, (*col, alpha), (r, r), r)
        surf.blit(gs, (int(cx) - r, int(cy) - r), special_flags=pygame.BLEND_RGBA_ADD)

    @staticmethod
    def _draw_heart(surf, col, cx, cy, s):
        r = s * 0.32
        pygame.draw.circle(surf, col, (int(cx - r), int(cy - r * 0.4)), int(r))
        pygame.draw.circle(surf, col, (int(cx + r), int(cy - r * 0.4)), int(r))
        pygame.draw.polygon(surf, col, [
            (cx - s * 0.62, cy - r * 0.5), (cx + s * 0.62, cy - r * 0.5), (cx, cy + s * 0.7),
        ])

    def draw(self, small_font):
        t = self.anim_t
        sprite = pygame.transform.scale(ASRIEL_IMAGE, (self.size, self.size))
        if self.is_vulnerable() or (self.pattern == "save_window" and self.state == "active"):
            tinted = sprite.copy()
            glow_amt = int(90 + 60 * math.sin(t * 0.2))
            tinted.fill((255, 255, glow_amt, 0), special_flags=pygame.BLEND_RGBA_ADD)
            sprite = tinted
        screen.blit(sprite, (int(self.x) - self.size // 2, int(self.y) - self.size // 2))

        p = self.pattern
        d = self.data
        RB = [(255, 80, 80), (255, 180, 60), (255, 240, 60),
              (80, 220, 90), (80, 160, 255), (180, 90, 255)]

        def rainbow(i):
            return RB[i % len(RB)]

        if p == "chaos_saber":
            for i, w in enumerate(d.get("waves", [])):
                if not w.get("alive", True):
                    continue
                wx = int(w["x"])
                col = rainbow(i)
                bright = tuple(min(255, c + 70) for c in col)
                segs = [(0, w["gap1"] - w["gap_h"] // 2),
                        (w["gap1"] + w["gap_h"] // 2, w["gap2"] - w["gap_h"] // 2),
                        (w["gap2"] + w["gap_h"] // 2, HEIGHT)]
                for top, bot in segs:
                    if bot <= top:
                        continue
                    gs = pygame.Surface((44, bot - top), pygame.SRCALPHA)
                    pygame.draw.rect(gs, (*col, 70), (2, 0, 40, bot - top))
                    screen.blit(gs, (wx - 22, top), special_flags=pygame.BLEND_RGBA_ADD)
                    pygame.draw.rect(screen, col, (wx - 8, top, 16, bot - top))
                    pygame.draw.rect(screen, bright, (wx - 9, top, 3, bot - top))
                    for sy in range(int(top) + 10, int(bot) - 10, 30):
                        if (sy + i * 13 + t) % 60 < 6:
                            pygame.draw.circle(screen, WHITE, (wx - 8 + 8, sy), 2)
                for gy in (w["gap1"], w["gap2"]):
                    self._glow(screen, (255, 255, 200), wx, gy, 22, alpha=50)

        elif p == "chaos_buster":
            for s in d.get("stars", []):
                if not s.get("alive", True):
                    continue
                self._glow(screen, YELLOW, s["x"], s["y"], 14, alpha=90)
                spin = math.atan2(s["vy"], s["vx"]) + t * 0.25
                self._draw_star(screen, YELLOW, s["x"], s["y"], 9, spin=spin, core=WHITE)
            if d.get("sub_phase") == "beam_warn":
                gs2 = d.get("beam_gap"); gap_h = 90
                y0, y1 = (gap_h, gap_h + 6) if gs2 == "top" else (HEIGHT - gap_h - 6, HEIGHT - gap_h)
                flick = 255 if (t // 4) % 2 == 0 else 90
                pygame.draw.rect(screen, (flick, 40, 40), (0, y0, WIDTH, 3))
                pygame.draw.rect(screen, (flick, 40, 40), (0, y1, WIDTH, 3))
                hs = pygame.Surface((WIDTH, abs(y1 - y0) + 6), pygame.SRCALPHA)
                hs.fill((255, 60, 60, 45))
                screen.blit(hs, (0, min(y0, y1)))
            elif d.get("sub_phase") == "beam":
                gs2 = d.get("beam_gap"); gap_h = 90
                by0, by1 = (gap_h, HEIGHT) if gs2 == "top" else (0, HEIGHT - gap_h)
                band = max(1, (by1 - by0) // 6)
                for i in range(6):
                    pygame.draw.rect(screen, rainbow(i + t // 3), (0, by0 + band * i, WIDTH, band + 1))
                edge_y = by0 if gs2 == "top" else by1 - 3
                pygame.draw.rect(screen, WHITE, (0, edge_y, WIDTH, 3))

        elif p == "shocker_breaker":
            for z in d.get("zones", []):
                if not z.get("alive", True):
                    continue
                col = rainbow(z["col"])
                if z["fuse"] > 0:
                    pulse = int(60 + 60 * math.sin(t * 0.4 + z["col"]))
                    s2 = pygame.Surface((z["w"], HEIGHT), pygame.SRCALPHA)
                    s2.fill((*col, pulse))
                    screen.blit(s2, (z["x"], 0))
                    ring_r = 14 + (45 - z["fuse"]) % 20
                    pygame.draw.circle(screen, RED, (z["x"] + z["w"] // 2, HEIGHT // 2), ring_r, 2)
                    warn_t = small_font.render("!", True, RED)
                    screen.blit(warn_t, (z["x"] + z["w"] // 2 - 4, HEIGHT // 2 - 10))
                else:
                    cx_b = z["x"] + z["w"] // 2
                    segs2 = 8
                    pts = [(cx_b + random.randint(-14, 14), int(HEIGHT * i / segs2)) for i in range(segs2 + 1)]
                    self._glow(screen, col, cx_b, HEIGHT // 2, z["w"] * 0.7, alpha=60)
                    pygame.draw.lines(screen, col, False, pts, 8)
                    pygame.draw.lines(screen, WHITE, False, pts, 3)
                    fade = max(0, 255 - z["erupt"] * 12)
                    fs = pygame.Surface((z["w"], 30), pygame.SRCALPHA)
                    fs.fill((*col, fade))
                    screen.blit(fs, (z["x"], HEIGHT - 30))

        elif p == "star_blaster":
            for bs in d.get("big_stars", []):
                if not bs.get("alive", True):
                    continue
                if bs["warn"] > 0:
                    if (bs["warn"] // 3) % 2 == 0:
                        pygame.draw.line(screen, (255, 255, 150),
                                          (int(bs["x"]), 0), (int(bs["x"]), HEIGHT - 40), 2)
                    pygame.draw.circle(screen, (255, 255, 150), (int(bs["x"]), HEIGHT - 40), 10, 2)
                else:
                    self._glow(screen, YELLOW, bs["x"], bs["y"], 30, alpha=80)
                    self._draw_star(screen, YELLOW, bs["x"], bs["y"], 20, spin=t * 0.15, core=WHITE)
            for f in d.get("frags", []):
                if not f.get("alive", True):
                    continue
                tail_x, tail_y = f["x"] - f["vx"] * 2.2, f["y"] - f["vy"] * 2.2
                pygame.draw.line(screen, (255, 200, 80), (tail_x, tail_y), (f["x"], f["y"]), 2)
                self._draw_star(screen, YELLOW, f["x"], f["y"], 7, spin=t * 0.3, core=WHITE, n=4)

        elif p == "hyper_goner":
            cx, cy = int(d.get("pull_x", WIDTH // 2)), int(d.get("pull_y", HEIGHT // 2))
            for k in range(3):
                ang = t * 0.05 + k * 2.09
                rr = 46 + 6 * math.sin(t * 0.1 + k)
                arc_pts = [(cx + rr * math.cos(ang + j * 0.3), cy + rr * math.sin(ang + j * 0.3))
                           for j in range(6)]
                pygame.draw.lines(screen, (150, 0, 0), False, arc_pts, 2)
            self._glow(screen, (120, 0, 0), cx, cy, 40, alpha=70)
            pygame.draw.circle(screen, (8, 8, 8), (cx, cy), 32)
            pygame.draw.circle(screen, (220, 0, 0), (cx - 11, cy - 4), 5)
            pygame.draw.circle(screen, (220, 0, 0), (cx + 11, cy - 4), 5)
            jaw = [(cx - 20, cy + 10)]
            for j in range(5):
                jx = cx - 20 + j * 10
                jaw.append((jx, cy + (20 if j % 2 == 0 else 12)))
            jaw.append((cx + 20, cy + 10))
            pygame.draw.lines(screen, (230, 230, 230), False, jaw, 2)
            for f in d.get("frags", []):
                if not f.get("alive", True):
                    continue
                tail_x, tail_y = f["x"] - f["vx"] * 2.0, f["y"] - f["vy"] * 2.0
                pygame.draw.line(screen, (255, 180, 60), (tail_x, tail_y), (f["x"], f["y"]), 2)
                self._draw_star(screen, (255, 220, 80), f["x"], f["y"], 6, spin=t * 0.3, core=WHITE, n=4)

        elif p == "angels_ray":
            for r in d.get("rays", []):
                if not r.get("alive", True):
                    continue
                tail_x, tail_y = r["x"] - r["vx"] * 2.5, r["y"] - r["vy"] * 2.5
                pygame.draw.line(screen, (180, 220, 255), (tail_x, tail_y), (r["x"], r["y"]), 2)
                self._glow(screen, (180, 220, 255), r["x"], r["y"], 12, alpha=90)
                spin = math.atan2(r["vy"], r["vx"])
                self._draw_star(screen, (200, 230, 255), r["x"], r["y"], 8, spin=spin, core=WHITE, n=4)

        elif p == "endless_comet":
            for i, c in enumerate(d.get("comets", [])):
                if not c.get("alive", True):
                    continue
                col = rainbow(i)
                tail_x, tail_y = c["x"] - c["vx"] * 3.2, c["y"] - c["vy"] * 3.2
                pygame.draw.line(screen, col, (tail_x, tail_y), (c["x"], c["y"]), 3)
                self._glow(screen, col, c["x"], c["y"], 10, alpha=90)
                pygame.draw.circle(screen, WHITE, (int(c["x"]), int(c["y"])), 3)

        elif p == "final_beam":
            gs2 = d.get("gap_side"); gap_h = d.get("gap_h", 60)
            if d.get("sub_phase") == "warn":
                ly = gap_h if gs2 == "top" else HEIGHT - gap_h
                flick = 255 if (t // 3) % 2 == 0 else 100
                pygame.draw.line(screen, (flick, 30, 30), (0, ly), (WIDTH, ly), 3)
                for hx in range(0, WIDTH, 20):
                    hy0 = ly + (10 if gs2 == "top" else -10)
                    pygame.draw.line(screen, (flick, 30, 30), (hx, ly), (hx + 10, hy0), 2)
            else:
                by0, by1 = (gap_h, HEIGHT) if gs2 == "top" else (0, HEIGHT - gap_h)
                band = max(1, (by1 - by0) // 8)
                for i in range(8):
                    pygame.draw.rect(screen, rainbow(i + t // 2), (0, by0 + band * i, WIDTH, band + 1))
                for sx in range(0, WIDTH, 26):
                    sy = by0 + int((by1 - by0) * ((sx + t * 3) % WIDTH) / WIDTH)
                    pygame.draw.circle(screen, WHITE, (sx, sy), 2)
                edge_y = by0 if gs2 == "top" else by1 - 3
                pygame.draw.rect(screen, WHITE, (0, edge_y, WIDTH, 3))

        elif p == "save_window":
            pulse = 1.0 + 0.12 * math.sin(t * 0.12)
            gw, gh = int((self.size + 50) * pulse), int((self.size + 50) * pulse)
            glow = pygame.Surface((gw, gh), pygame.SRCALPHA)
            pygame.draw.circle(glow, (255, 255, 180, 80), (gw // 2, gh // 2), gw // 2)
            screen.blit(glow, (int(self.x) - gw // 2, int(self.y) - gh // 2))
            for k in range(8):
                ang = t * 0.02 + k * math.pi / 4
                ex = self.x + math.cos(ang) * (self.size // 2 + 30)
                ey = self.y + math.sin(ang) * (self.size // 2 + 30)
                pygame.draw.line(screen, (255, 250, 200), (self.x, self.y), (ex, ey), 1)
            heart_y = self.y - self.size // 2 - 30 + int(4 * math.sin(t * 0.15))
            self._draw_heart(screen, (255, 60, 90), self.x, heart_y, 18)

        if self.quote_timer > 0 and self.pattern in self.PATTERN_QUOTE:
            q = self.PATTERN_QUOTE[self.pattern]
            qt = small_font.render(q, True, (255, 240, 200))
            qt.set_alpha(min(255, self.quote_timer * 4))
            screen.blit(qt, (WIDTH // 2 - qt.get_width() // 2, HEIGHT - 58))

        bar_w = 240
        pygame.draw.rect(screen, (60, 60, 60), (WIDTH // 2 - bar_w // 2, 16, bar_w, 16))
        if not self.phase2:
            pygame.draw.rect(screen, (200, 120, 255),
                              (WIDTH // 2 - bar_w // 2, 16,
                               int(bar_w * max(self.hp, 0) / self.max_hp), 16))
            name_text = small_font.render(self.name, True, WHITE)
            screen.blit(name_text, (WIDTH // 2 - name_text.get_width() // 2, 34))
        else:
            seg = 12
            for i in range(bar_w // seg):
                pygame.draw.rect(screen, rainbow(i + t // 4),
                                  (WIDTH // 2 - bar_w // 2 + i * seg, 16, seg, 16))
            label = self.name + "  [ABSOLUTE GOD - INVINCIBLE]"
            name_text = small_font.render(label, True, WHITE)
            screen.blit(name_text, (WIDTH // 2 - name_text.get_width() // 2, 34))

        for pt in self.hit_particles:
            ratio = pt["life"] / pt["max_life"]
            pygame.draw.circle(screen, (int(255 * ratio), int(220 * ratio), int(120 * ratio)),
                                (int(pt["x"]), int(pt["y"])), max(1, int(5 * ratio)))


def fight_one_boss(player, boss, small_font, particle_colors=None):
    """보스 하나와 싸운다. 'win', 'lose', 'quit' 중 하나를 반환."""
    result = None
    move_particles = []
    prev_x, prev_y = player.x, player.y
    screen_shake = 0

    while result is None:
        for event in poll_events():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    result = "quit"
                if event.key == pygame.K_SPACE:
                    player.try_dash()
                if event.key == pygame.K_e:
                    player.try_heal()

        keys = pygame.key.get_pressed()
        player.handle_move(keys)
        player.update()
        boss.update(player)

        if player.wall_hit_shake:
            screen_shake = 12

        if player.dashing and player.get_rect().colliderect(boss.get_rect()):
            boss.take_damage(2)

        if player.hp <= 0:
            result = "lose"
        elif boss.hp <= 0:
            result = "win"

        # 이동 파티클 생성
        if particle_colors:
            if abs(player.x - prev_x) > 0.3 or abs(player.y - prev_y) > 0.3 or player.dashing:
                for _ in range(2):
                    col = random.choice(particle_colors)
                    a = random.uniform(0, 2 * math.pi)
                    spd = random.uniform(1.0, 3.0)
                    move_particles.append({
                        "x": float(player.x), "y": float(player.y),
                        "vx": math.cos(a) * spd, "vy": math.sin(a) * spd,
                        "life": random.randint(10, 20), "max_life": 20, "color": col,
                    })
        prev_x, prev_y = player.x, player.y
        for p in move_particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= 1
        move_particles = [p for p in move_particles if p["life"] > 0]

        screen.fill(BLACK)
        boss.draw(small_font)
        for p in move_particles:
            ratio = p["life"] / p["max_life"]
            r, g, b = p["color"]
            pygame.draw.circle(screen, (int(r * ratio), int(g * ratio), int(b * ratio)),
                               (int(p["x"]), int(p["y"])), max(1, int(4 * ratio)))
        player.draw()

        _phb_w = 160
        pygame.draw.rect(screen, (50, 50, 50), (12, HEIGHT - 32, _phb_w, 14))
        pygame.draw.rect(screen, (80, 220, 80),
                         (12, HEIGHT - 32, int(_phb_w * max(player.hp, 0) / player.max_hp), 14))
        _php_t = small_font.render(f"HP {player.hp}/{player.max_hp}", True, (180, 255, 180))
        screen.blit(_php_t, (12, HEIGHT - 50))
        _heal_cd = player.heal_cooldown
        _heal_col = (80, 255, 150) if _heal_cd == 0 else (120, 120, 120)
        _heal_w = _phb_w - int(_phb_w * _heal_cd / player.HEAL_MAX_CD)
        pygame.draw.rect(screen, (30, 60, 30), (12, HEIGHT - 62, _phb_w, 8))
        pygame.draw.rect(screen, _heal_col,    (12, HEIGHT - 62, _heal_w, 8))
        _heal_lbl = "E: 회복 [준비됨]" if _heal_cd == 0 else f"E: 회복 ({_heal_cd // 60 + 1}s)"
        _heal_t = small_font.render(_heal_lbl, True, _heal_col)
        screen.blit(_heal_t, (12, HEIGHT - 78))
        hint = small_font.render("이동: WASD/방향키   돌진공격: SPACE   나가기: ESC", True, WHITE)
        screen.blit(hint, (20, HEIGHT - 30))

        # 벽 충돌 진동 효과: 현재 프레임을 흔들어서 재블릿
        if screen_shake > 0:
            frame = screen.copy()
            ox = random.randint(-screen_shake, screen_shake)
            oy = random.randint(-screen_shake, screen_shake)
            screen.fill(BLACK)
            screen.blit(frame, (ox, oy))
            screen_shake = max(0, screen_shake - 1)

        present()
        clock.tick(FPS)

    message = {"win": f"{boss.name} DEFEATED!", "lose": "GAME OVER", "quit": ""}[result]
    if message:
        screen.fill(BLACK)
        text = font.render(message, True, WHITE)
        screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 2 - 20))
        present()
        pygame.time.wait(1500)

    return result


def fight_orange_mirror(player, small_font):
    """히든 보스전. 인트로/전투/아웃트로 포함."""
    boss = OrangeMirrorBoss()

    # ── 인트로: 2.5초 대칭 등장 ──
    player.x = 120.0
    player.y = float(HEIGHT // 2)
    player.knockback_vx = 0.0
    player.knockback_vy = 0.0
    player.dashing = False
    boss.x = float(WIDTH - 120)
    boss.y = float(HEIGHT // 2)

    for frame in range(150):
        for event in poll_events():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        screen.fill(BLACK)
        player.draw()
        pygame.draw.rect(screen, ORANGE, boss.get_rect())
        cx, cy, h = int(boss.x), int(boss.y), boss.size // 2
        pygame.draw.line(screen, BLACK, (cx - h, cy), (cx + h, cy), 2)
        pygame.draw.line(screen, BLACK, (cx, cy - h), (cx, cy + h), 2)
        title = small_font.render("???", True, ORANGE)
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 2 - 55))
        present()
        clock.tick(FPS)

    # ── 전투 ──
    player.parry_enabled = True
    _mirror_colors = [GREEN, WHITE, RED]
    move_particles = []
    prev_x, prev_y = player.x, player.y
    parry_flash = 0   # 패리 성공 시 화면 번쩍임
    result = None
    while result is None:
        for event in poll_events():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    result = "quit"
                if event.key == pygame.K_SPACE:
                    player.try_dash()
                if event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                    player.try_parry()
                if event.key == pygame.K_e:
                    player.try_heal()

        keys = pygame.key.get_pressed()
        player.handle_move(keys)
        player.update()
        boss.update(player)

        # 취약 상태일 때만 보스 본체에 데미지
        if player.dashing and player.get_rect().colliderect(boss.get_rect()):
            boss.take_damage(2)

        # 분열 미니 사각형은 대쉬로 파괴 가능
        if player.dashing and boss.pattern == "split_squares" and boss.state == "active":
            for mini in boss.data.get("minis", []):
                if mini.get("alive"):
                    mini_rect = pygame.Rect(int(mini["x"]) - 6, int(mini["y"]) - 6, 13, 13)
                    if player.get_rect().colliderect(mini_rect):
                        mini["alive"] = False

        # 패리 성공 여부는 take_damage 반환값으로 감지 (boss.update 내부에서 발생)
        # → 이전 hit_cooldown 변화로 간접 감지
        prev_hit_cd = player.hit_cooldown

        keys = None  # update 후 재사용 방지 (이미 위에서 처리)

        if player.hp <= 0:
            result = "lose"
        elif boss.hp <= 0:
            result = "win"

        # 패리 성공 시 화면 번쩍임 (hit_cooldown이 짧게(20) 세팅된 경우)
        if player.hit_cooldown == 20 and prev_hit_cd != 20:
            parry_flash = 12
        if parry_flash > 0:
            parry_flash -= 1

        # 이동 파티클 (초록+하양+빨강)
        if abs(player.x - prev_x) > 0.3 or abs(player.y - prev_y) > 0.3 or player.dashing:
            for _ in range(2):
                col = random.choice(_mirror_colors)
                a = random.uniform(0, 2 * math.pi)
                spd = random.uniform(1.0, 3.0)
                move_particles.append({
                    "x": float(player.x), "y": float(player.y),
                    "vx": math.cos(a) * spd, "vy": math.sin(a) * spd,
                    "life": random.randint(10, 20), "max_life": 20, "color": col,
                })
        prev_x, prev_y = player.x, player.y
        for p in move_particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= 1
        move_particles = [p for p in move_particles if p["life"] > 0]

        screen.fill(BLACK)

        # 패리 성공 번쩍임
        if parry_flash > 0:
            flash_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            flash_surf.fill((180, 0, 255, int(180 * parry_flash / 12)))
            screen.blit(flash_surf, (0, 0))

        boss.draw(small_font)
        for p in move_particles:
            ratio = p["life"] / p["max_life"]
            r, g, b = p["color"]
            pygame.draw.circle(screen, (int(r * ratio), int(g * ratio), int(b * ratio)),
                               (int(p["x"]), int(p["y"])), max(1, int(4 * ratio)))
        player.draw()

        # 패리 상태 UI + HP bar + heal
        _phb_w2 = 160
        pygame.draw.rect(screen, (50, 50, 50), (12, HEIGHT - 32, _phb_w2, 14))
        pygame.draw.rect(screen, (80, 220, 80),
                         (12, HEIGHT - 32, int(_phb_w2 * max(player.hp, 0) / player.max_hp), 14))
        _php_t2 = small_font.render(f"HP {player.hp}/{player.max_hp}", True, (180, 255, 180))
        screen.blit(_php_t2, (12, HEIGHT - 50))
        _hcd2 = player.heal_cooldown
        _hcol2 = (80, 255, 150) if _hcd2 == 0 else (120, 120, 120)
        _hw2 = _phb_w2 - int(_phb_w2 * _hcd2 / player.HEAL_MAX_CD)
        pygame.draw.rect(screen, (30, 60, 30), (12, HEIGHT - 62, _phb_w2, 8))
        pygame.draw.rect(screen, _hcol2,      (12, HEIGHT - 62, _hw2, 8))
        _hlbl2 = "E: 회복 [준비됨]" if _hcd2 == 0 else f"E: 회복 ({_hcd2 // 60 + 1}s)"
        screen.blit(small_font.render(_hlbl2, True, _hcol2), (12, HEIGHT - 78))
        if player.parry_timer > 0:
            parry_text = small_font.render("★ PARRY READY ★", True, (200, 0, 255))
            screen.blit(parry_text, (WIDTH // 2 - parry_text.get_width() // 2, HEIGHT - 55))
        elif parry_flash > 0:
            parry_text = small_font.render("PARRIED!", True, (200, 0, 255))
            screen.blit(parry_text, (WIDTH // 2 - parry_text.get_width() // 2, HEIGHT - 55))

        # 취약 상태일 때 남은 공격 시간 표시
        if boss.state == "vulnerable":
            ratio = boss.timer / 120
            bar_w = 200
            pygame.draw.rect(screen, (60, 60, 60), (WIDTH // 2 - bar_w // 2, HEIGHT - 22, bar_w, 8))
            pygame.draw.rect(screen, YELLOW, (WIDTH // 2 - bar_w // 2, HEIGHT - 22, int(bar_w * ratio), 8))
            atk_text = small_font.render("ATTACK NOW!", True, YELLOW)
            screen.blit(atk_text, (WIDTH // 2 - atk_text.get_width() // 2, HEIGHT - 40))

        hint = small_font.render("이동: WASD   돌진: SPACE   방어(근접): SHIFT   나가기: ESC", True, (120, 120, 120))
        screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 14))
        present()
        clock.tick(FPS)

    player.parry_enabled = False

    if result == "win":
        # ── 아웃트로: 보스가 주인공 색으로 변하며 흡수 ──
        for i in range(120):
            for event in poll_events():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
            ratio = i / 120.0
            r = int(ORANGE[0] * (1 - ratio))
            g = int(ORANGE[1] * (1 - ratio) + 220 * ratio)
            b = int(220 * ratio)
            boss.x += (player.x - boss.x) * 0.06
            boss.y += (player.y - boss.y) * 0.06
            boss_s = max(2, int(boss.size * (1 - ratio * 0.9)))
            screen.fill(BLACK)
            player.draw()
            pygame.draw.rect(screen, (r, g, b),
                             pygame.Rect(int(boss.x) - boss_s // 2, int(boss.y) - boss_s // 2, boss_s, boss_s))
            present()
            clock.tick(FPS)
        screen.fill(BLACK)
        msg = font.render("TRUE VICTORY", True, ORANGE)
        screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2 - 20))
        present()
        pygame.time.wait(2500)
    elif result == "lose":
        screen.fill(BLACK)
        msg = font.render("GAME OVER", True, WHITE)
        screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2 - 20))
        present()
        pygame.time.wait(1500)

    return result


def run_boss_fight():
    """치트코드로 진입하는 보스전. 보스를 순서대로 모두 처치하면 'win'을 반환."""
    pygame.mixer.music.load("assets/boss_music.mp3")
    pygame.mixer.music.play(-1)

    player = BossPlayer()
    small_font = pygame.font.SysFont(None, 28)

    # (보스 클래스, 이 전투에서의 체력, 이동 파티클 색상 목록)
    phase_configs = [
        (DragonBoss,    10, []),                   # 드래곤: 변화 없음
        (KnightBoss,    12, [GREEN]),              # 기사: 체력12, 초록 파티클
        (DemonLordBoss, 20, [GREEN, WHITE]),       # 마왕: 체력20, 초록+하양 파티클
    ]

    result = "win"
    for boss_cls, hp, colors in phase_configs:
        player.max_hp = hp
        player.hp = hp
        boss = boss_cls()
        result = fight_one_boss(player, boss, small_font, particle_colors=colors or None)
        if result != "win":
            break

    # 3보스 모두 클리어 시 히든 보스 등장 (체력 23, 초록+하양+빨강 파티클)
    if result == "win":
        player.max_hp = 23
        player.hp = 23
        result = fight_orange_mirror(player, small_font)

    pygame.mixer.music.load("assets/geodash_music.mp3")
    pygame.mixer.music.play(-1)
    return result


def fight_papyrus(player, small_font):
    try:
        pygame.mixer.music.load("assets/boss_music.mp3")
        pygame.mixer.music.play(-1)
    except Exception:
        pass

    boss = PapyrusBoss()
    clock_p = pygame.time.Clock()

    # ── 인트로 대사 ──
    INTRO = [
        "* HUMAN! DO NOT TAKE ANOTHER STEP!",
        "* I, THE GREAT PAPYRUS, AM BLOCKING YOUR WAY!",
        "* NYEH HEH HEH!",
        "* TODAY IS THE DAY PAPYRUS CAPTURES A HUMAN!",
        "* AND THEN MAYBE SANS WILL FINALLY BE PROUD OF ME!",
        "* ARE YOU READY?",
        "* ...WELL, READY OR NOT, HERE I COME!",
    ]
    sprite_p = pygame.transform.scale(PAPYRUS_IMAGE, (170, 170))
    dlg_idx = 0
    dlg_running = True
    while dlg_running and dlg_idx < len(INTRO):
        for ev in poll_events():
            if ev.type == pygame.QUIT:
                pygame.quit(); return "quit"
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    dlg_running = False
                elif ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z):
                    dlg_idx += 1
        screen.fill((10, 10, 20))
        screen.blit(sprite_p, (WIDTH * 3 // 4 - 85, HEIGHT // 2 - 85))
        bx, by, bw, bh2 = 30, HEIGHT // 2 - 90, WIDTH * 3 // 4 - 60, 190
        pygame.draw.rect(screen, (20, 20, 40), (bx, by, bw, bh2), border_radius=8)
        pygame.draw.rect(screen, (200, 120, 60), (bx, by, bw, bh2), 2, border_radius=8)
        shown = INTRO[max(0, dlg_idx - 3): dlg_idx + 1]
        for i, ln in enumerate(shown):
            alpha = 255 if i == len(shown) - 1 else 110
            lt = small_font.render(ln, True, (255, 220, 180))
            lt.set_alpha(alpha)
            screen.blit(lt, (bx + 14, by + 14 + i * 38))
        adv = small_font.render("SPACE/ENTER : next   ESC : skip", True, (130, 130, 150))
        screen.blit(adv, (bx + 14, by + bh2 - 26))
        prog = small_font.render(f"{min(dlg_idx+1, len(INTRO))}/{len(INTRO)}", True, (90, 90, 110))
        screen.blit(prog, (bx + bw - prog.get_width() - 14, by + 10))
        present()
        clock_p.tick(60)

    # ── 전투 ──
    player.max_hp = 30
    player.hp = 30
    result = "lose"
    shake = 0
    running = True
    grav_vy = 0.0        # blue soul gravity accumulator
    dash_evaluated = False
    BLUE_SOUL_PATS = ("blue_soul", "blue_bones_mix")

    # Annoying dog cutscene (inline)
    def _dog_cutscene():
        lines = [
            "* NYEH HEH HEH! NOW I SHALL USE...",
            "* MY SPECIAL ATTACK!",
            "...                              ",
            "* ...WOWIE, THAT BLASTED DOG.",
            "* I... I STILL HAVE COOL DUDE!",
        ]
        dlg2 = 0; timer2 = 0; shown2 = []
        while dlg2 < len(lines):
            for ev in poll_events():
                if ev.type == pygame.QUIT:
                    pygame.quit(); return
                if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_SPACE, pygame.K_RETURN):
                    shown2.append(lines[dlg2]); dlg2 += 1; timer2 = 0
            timer2 += 1
            if dlg2 < len(lines) and timer2 >= 75:
                shown2.append(lines[dlg2]); dlg2 += 1; timer2 = 0

            screen.fill((10, 10, 20))
            boss.draw(small_font)

            # Dog running across
            t_frac = min(1.0, timer2 / 40.0) if dlg2 >= 2 else 0.0
            dog_x2 = int(-60 + (WIDTH + 120) * t_frac)
            if dlg2 >= 2:
                pygame.draw.ellipse(screen, WHITE, (dog_x2 - 25, HEIGHT // 2 - 18, 50, 36))
                pygame.draw.ellipse(screen, WHITE, (dog_x2 - 5, HEIGHT // 2 - 30, 18, 20))
                pygame.draw.circle(screen, BLACK, (dog_x2 + 8, HEIGHT // 2 - 8), 4)
                # bone the dog stole
                bx_dog = dog_x2 + 30
                pygame.draw.line(screen, WHITE, (bx_dog, HEIGHT // 2 - 5),
                                 (bx_dog + 80, HEIGHT // 2 - 5), 14)
                pygame.draw.circle(screen, WHITE, (bx_dog, HEIGHT // 2 - 5), 12)
                pygame.draw.circle(screen, WHITE, (bx_dog + 80, HEIGHT // 2 - 5), 12)

            box2_x, box2_y, box2_w, box2_h = WIDTH // 2 - 220, HEIGHT // 2 + 60, 440, 12 + min(len(shown2), 4) * 34 + 10
            pygame.draw.rect(screen, (20, 20, 40), (box2_x, box2_y, box2_w, box2_h), border_radius=7)
            pygame.draw.rect(screen, (200, 120, 60), (box2_x, box2_y, box2_w, box2_h), 2, border_radius=7)
            for i, ln2 in enumerate(shown2[-4:]):
                alpha2 = 255 if i == min(len(shown2), 4) - 1 else 110
                lt2 = small_font.render(ln2, True, (255, 220, 180))
                lt2.set_alpha(alpha2); screen.blit(lt2, (box2_x + 12, box2_y + 10 + i * 34))
            present()
            clock_p.tick(60)

    while running:
        for event in poll_events():
            if event.type == pygame.QUIT:
                pygame.quit(); return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False; result = "lose"
                elif event.key == pygame.K_SPACE:
                    player.try_dash()
                elif event.key == pygame.K_e:
                    player.try_heal()

        keys = pygame.key.get_pressed()
        player.handle_move(keys)
        player.update()

        # Blue soul gravity
        if boss.pattern in BLUE_SOUL_PATS and boss.state == "active":
            grav_vy = min(grav_vy + 1.0, 6.0)
            player.knockback_vy += grav_vy
        else:
            grav_vy = max(grav_vy - 0.5, 0.0)

        boss.update(player)

        # Annoying dog cutscene trigger
        if (boss.pattern == "annoying_dog" and boss.state == "active"
                and boss.data.get("dog_phase") == "done" and boss.data.get("dog_timer", 0) == 31):
            _dog_cutscene()

        # Dash damage (1회/대시)
        if not player.dashing:
            dash_evaluated = False
        if player.dashing and not dash_evaluated and boss.get_rect().colliderect(player.get_rect()):
            dash_evaluated = True
            if boss.is_vulnerable():
                boss.take_damage(2)
                shake = max(shake, 5)

        if player.hp <= 0:
            result = "lose"; running = False
        elif boss.hp <= 0:
            result = "win"; running = False

        # ── 그리기 ──
        screen.fill((10, 10, 20))
        blue_mode = (boss.pattern in BLUE_SOUL_PATS and boss.state == "active")
        boss.draw(small_font, blue_soul_mode=blue_mode)

        # Blue soul: player tint
        if blue_mode and not player.dashing:
            pygame.draw.rect(screen, (20, 60, 200), player.get_rect())
            if player.hit_cooldown > 0 and player.hit_cooldown % 10 < 5:
                pygame.draw.rect(screen, (100, 150, 255), player.get_rect(), 2)
        else:
            player.draw()

        turn_txt = small_font.render(f"Turn {boss.turn}/{len(boss.TURN_SEQ)}", True, (200, 200, 200))
        screen.blit(turn_txt, (WIDTH - turn_txt.get_width() - 12, 14))

        # Player HP bar + heal indicator (bottom-left)
        _phb_w = 160
        pygame.draw.rect(screen, (50, 50, 50), (12, HEIGHT - 32, _phb_w, 14))
        pygame.draw.rect(screen, (80, 220, 80),
                         (12, HEIGHT - 32, int(_phb_w * max(player.hp, 0) / player.max_hp), 14))
        _php_t = small_font.render(f"HP {player.hp}/{player.max_hp}", True, (180, 255, 180))
        screen.blit(_php_t, (12, HEIGHT - 50))
        _hcd_p = player.heal_cooldown
        _hcol_p = (80, 255, 150) if _hcd_p == 0 else (120, 120, 120)
        _hw_p = _phb_w - int(_phb_w * _hcd_p / player.HEAL_MAX_CD)
        pygame.draw.rect(screen, (30, 60, 30), (12, HEIGHT - 62, _phb_w, 8))
        pygame.draw.rect(screen, _hcol_p,      (12, HEIGHT - 62, _hw_p, 8))
        _hlbl_p = "E: 회복 [준비됨]" if _hcd_p == 0 else f"E: 회복 ({_hcd_p // 60 + 1}s)"
        screen.blit(small_font.render(_hlbl_p, True, _hcol_p), (12, HEIGHT - 78))

        if shake > 0:
            frame_copy = screen.copy()
            ox = random.randint(-shake, shake)
            oy = random.randint(-shake, shake)
            screen.fill(BLACK)
            screen.blit(frame_copy, (ox, oy))
            shake -= 1

        present()
        clock_p.tick(60)

    # ── 결과 ──
    if result == "win":
        DEATH_D = [
            ("* ...", 60),
            ("* THAT'S OKAY.", 65),
            ("* I KNEW YOU COULD DO IT.", 70),
            ("* SANS ALWAYS SAID YOU WERE SPECIAL.", 75),
            ("* I SUPPOSE HE WAS RIGHT.", 70),
            ("* ...", 55),
            ("* TAKE CARE OF HIM, OKAY?", 80),
            ("* HE ACTS COOL, BUT...", 70),
            ("* HE WORRIES.", 80),
            ("* NYEH HEH HEH.", 75),
        ]
        dead_img_p = pygame.transform.scale(PAPYRUS_DEAD_IMAGE, (200, 200))
        shown_d = []; dlg_d = 0; line_timer = 0
        while dlg_d < len(DEATH_D):
            for ev in poll_events():
                if ev.type == pygame.QUIT:
                    pygame.quit(); return "quit"
                if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_SPACE, pygame.K_RETURN):
                    if dlg_d < len(DEATH_D):
                        shown_d.append(DEATH_D[dlg_d][0]); dlg_d += 1; line_timer = 0
            line_timer += 1
            if dlg_d < len(DEATH_D) and line_timer >= DEATH_D[dlg_d][1]:
                shown_d.append(DEATH_D[dlg_d][0]); dlg_d += 1; line_timer = 0

            screen.fill((10, 10, 20))
            screen.blit(dead_img_p, (WIDTH // 2 - 100, HEIGHT // 2 - 180))
            box3_x = WIDTH // 2 - 220; box3_y = HEIGHT // 2 + 30
            box3_w = 440; box3_h = 14 + min(len(shown_d), 5) * 30 + 14
            pygame.draw.rect(screen, (18, 18, 35), (box3_x, box3_y, box3_w, box3_h), border_radius=8)
            pygame.draw.rect(screen, (200, 120, 60), (box3_x, box3_y, box3_w, box3_h), 2, border_radius=8)
            for i, msg in enumerate(shown_d[-5:]):
                alpha3 = 255 if i == min(len(shown_d), 5) - 1 else 120
                ts3 = small_font.render(msg, True, (255, 220, 180))
                ts3.set_alpha(alpha3)
                screen.blit(ts3, (box3_x + 12, box3_y + 10 + i * 30))
            adv3 = small_font.render("SPACE/ENTER : next", True, (100, 100, 120))
            screen.blit(adv3, (box3_x + box3_w - adv3.get_width() - 10, box3_y + box3_h - 22))
            present()
            clock_p.tick(60)

        # Final pause
        ft = 140
        while ft > 0:
            for ev in poll_events():
                if ev.type == pygame.QUIT:
                    pygame.quit(); return "quit"
                if ev.type == pygame.KEYDOWN:
                    ft = 0
            screen.fill((10, 10, 20))
            screen.blit(dead_img_p, (WIDTH // 2 - 100, HEIGHT // 2 - 180))
            box3_y2 = HEIGHT // 2 + 30
            pygame.draw.rect(screen, (18, 18, 35), (box3_x, box3_y2, box3_w, box3_h), border_radius=8)
            pygame.draw.rect(screen, (200, 120, 60), (box3_x, box3_y2, box3_w, box3_h), 2, border_radius=8)
            for i, msg in enumerate(shown_d[-5:]):
                alpha3 = 255 if i == min(len(shown_d), 5) - 1 else 120
                ts3 = small_font.render(msg, True, (255, 220, 180))
                ts3.set_alpha(alpha3)
                screen.blit(ts3, (box3_x + 12, box3_y2 + 10 + i * 30))
            done3 = small_font.render("[Press any key]", True, YELLOW)
            screen.blit(done3, (WIDTH // 2 - done3.get_width() // 2, box3_y2 + box3_h + 10))
            if ft < 40:
                fd = pygame.Surface((WIDTH, HEIGHT))
                fd.fill(BLACK); fd.set_alpha(int(255 * (1 - ft / 40)))
                screen.blit(fd, (0, 0))
            present()
            clock_p.tick(60); ft -= 1
    else:
        et = 110
        while et > 0:
            for ev in poll_events():
                if ev.type == pygame.QUIT:
                    pygame.quit(); return "quit"
                if ev.type == pygame.KEYDOWN:
                    et = 0
            screen.fill(BLACK)
            msgs_l = [("* HUMAN! YOU HAVE DISAPPOINTED ME!", (255, 200, 150)),
                      ("", WHITE), ("YOU DIED", RED)]
            for i, (ln_l, col_l) in enumerate(msgs_l):
                ts_l = small_font.render(ln_l, True, col_l)
                screen.blit(ts_l, (WIDTH // 2 - ts_l.get_width() // 2, HEIGHT // 2 - 30 + i * 36))
            present()
            clock_p.tick(60); et -= 1

    return result


def fight_undyne(player, small_font):
    try:
        pygame.mixer.music.load("assets/boss_music.mp3")
        pygame.mixer.music.play(-1)
    except Exception:
        pass

    boss = UndyneBoss()
    clock_u = pygame.time.Clock()

    # ── 인트로 대사 ──
    INTRO = [
        "* Human! Stop right there!",
        "* I've been waiting a LONG time for this!",
        "* My name is Undyne, Captain of the Royal Guard!",
        "* And it is my DUTY to capture your SOUL!",
        "* Don't hold back. I certainly won't.",
        "* Now... LET'S BEGIN!",
    ]
    sprite_u = pygame.transform.scale(UNDYNE_IMAGE, (170, 170))
    dlg_idx = 0; dlg_running = True
    while dlg_running and dlg_idx < len(INTRO):
        for ev in poll_events():
            if ev.type == pygame.QUIT: pygame.quit(); return "quit"
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE: dlg_running = False
                elif ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z): dlg_idx += 1
        screen.fill((10, 10, 25))
        screen.blit(sprite_u, (WIDTH * 3 // 4 - 85, HEIGHT // 2 - 85))
        bx, by, bw, bh2 = 30, HEIGHT // 2 - 90, WIDTH * 3 // 4 - 60, 190
        pygame.draw.rect(screen, (15, 15, 40), (bx, by, bw, bh2), border_radius=8)
        pygame.draw.rect(screen, (80, 160, 255), (bx, by, bw, bh2), 2, border_radius=8)
        shown = INTRO[max(0, dlg_idx - 3): dlg_idx + 1]
        for i, ln in enumerate(shown):
            alpha = 255 if i == len(shown) - 1 else 110
            lt = small_font.render(ln, True, (180, 220, 255)); lt.set_alpha(alpha)
            screen.blit(lt, (bx + 14, by + 14 + i * 38))
        adv = small_font.render("SPACE/ENTER : next   ESC : skip", True, (100, 120, 150))
        screen.blit(adv, (bx + 14, by + bh2 - 26))
        present(); clock_u.tick(60)

    # ── 전투 ──
    player.max_hp = 30; player.hp = 30
    result = "lose"; shake = 0; running = True
    shield_dir = 0  # 0=UP 1=RIGHT 2=DOWN 3=LEFT
    dash_evaluated = False
    mid_dlg_done = set()

    # Mid-fight dialogue lines
    MID_DLG = {
        66: ["* Heh... Not bad, human!", "* But this is where things get SERIOUS!"],
        33: ["* You...! How are you still standing?!", "* Fine... I'll use my FULL POWER!"],
    }

    def _show_mid_dlg(lines):
        t = 160
        while t > 0:
            for ev in poll_events():
                if ev.type == pygame.QUIT: pygame.quit(); return
                if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_SPACE, pygame.K_RETURN):
                    t = 0
            screen.fill((10, 10, 25))
            boss.draw(small_font, shield_dir)
            bx2, by2, bw2, bh3 = WIDTH // 2 - 220, HEIGHT // 2 + 40, 440, 20 + len(lines) * 32
            pygame.draw.rect(screen, (15, 15, 40), (bx2, by2, bw2, bh3), border_radius=7)
            pygame.draw.rect(screen, (80, 160, 255), (bx2, by2, bw2, bh3), 2, border_radius=7)
            for i, ln in enumerate(lines):
                lt2 = small_font.render(ln, True, (180, 220, 255))
                screen.blit(lt2, (bx2 + 12, by2 + 10 + i * 32))
            present(); clock_u.tick(60); t -= 1

    while running:
        for event in poll_events():
            if event.type == pygame.QUIT: pygame.quit(); return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: running = False; result = "lose"
                elif event.key == pygame.K_SPACE: player.try_dash()
                elif event.key in (pygame.K_UP, pygame.K_w):    shield_dir = 0
                elif event.key in (pygame.K_RIGHT, pygame.K_d): shield_dir = 1
                elif event.key in (pygame.K_DOWN, pygame.K_s):  shield_dir = 2
                elif event.key in (pygame.K_LEFT, pygame.K_a):  shield_dir = 3
                elif event.key == pygame.K_e:     player.try_heal()

        green_soul = boss.is_green_soul() and boss.state == "active"

        if not green_soul and not player.dashing and player.bound_timer <= 0:
            keys = pygame.key.get_pressed()
            dx = dy = 0
            if keys[pygame.K_a]: dx -= 1
            if keys[pygame.K_d]: dx += 1
            if keys[pygame.K_w]: dy -= 1
            if keys[pygame.K_s]: dy += 1
            if dx or dy:
                length = math.hypot(dx, dy)
                dx, dy = dx / length, dy / length
                player.facing = (dx, dy)
                player.x = max(player.size, min(WIDTH - player.size, player.x + dx * player.speed))
                player.y = max(player.size, min(HEIGHT - player.size, player.y + dy * player.speed))
        player.update()
        if green_soul:
            # Force position AFTER update so knockback can't drift the player
            player.x = float(UndyneBoss._GS_CX)
            player.y = float(UndyneBoss._GS_CY)
            player.knockback_vx = 0.0
            player.knockback_vy = 0.0

        # Dash damage (red soul only)
        if not player.dashing:
            dash_evaluated = False
        if (player.dashing and not dash_evaluated
                and boss.get_rect().colliderect(player.get_rect())):
            dash_evaluated = True
            if boss.is_vulnerable():
                boss.take_damage(2); shake = max(shake, 5)

        boss.update(player, shield_dir)

        # Mid-fight dialogue triggers
        hp_pct = int(boss.hp / boss.max_hp * 100)
        for threshold, lines in MID_DLG.items():
            if threshold not in mid_dlg_done and hp_pct <= threshold:
                mid_dlg_done.add(threshold)
                _show_mid_dlg(lines)

        if player.hp <= 0: result = "lose"; running = False
        elif boss.hp <= 0: result = "win"; running = False

        # ── 그리기 ──
        screen.fill((10, 10, 25))
        boss.draw(small_font, shield_dir)

        if green_soul:
            # In green soul: draw player as soul diamond (not normal sprite)
            pass  # soul already drawn inside boss.draw
        else:
            player.draw()

        # Player HP bar + heal indicator (bottom-left)
        _phb_w = 160
        pygame.draw.rect(screen, (50, 50, 50), (12, HEIGHT - 32, _phb_w, 14))
        hp_ratio = max(player.hp, 0) / player.max_hp
        pygame.draw.rect(screen, (80, 220, 80),
                         (12, HEIGHT - 32, int(_phb_w * hp_ratio), 14))
        _php_t = small_font.render(f"HP {player.hp}/{player.max_hp}", True, (180, 255, 180))
        screen.blit(_php_t, (12, HEIGHT - 50))
        _hcd_u = player.heal_cooldown
        _hcol_u = (80, 255, 150) if _hcd_u == 0 else (120, 120, 120)
        _hw_u = _phb_w - int(_phb_w * _hcd_u / player.HEAL_MAX_CD)
        pygame.draw.rect(screen, (30, 60, 30), (12, HEIGHT - 62, _phb_w, 8))
        pygame.draw.rect(screen, _hcol_u,      (12, HEIGHT - 62, _hw_u, 8))
        _hlbl_u = "E: 회복 [준비됨]" if _hcd_u == 0 else f"E: 회복 ({_hcd_u // 60 + 1}s)"
        screen.blit(small_font.render(_hlbl_u, True, _hcol_u), (12, HEIGHT - 78))

        turn_txt = small_font.render(f"Turn {boss.turn}/{len(boss.TURN_SEQ)}", True, (200, 200, 200))
        screen.blit(turn_txt, (WIDTH - turn_txt.get_width() - 12, 14))

        if shake > 0:
            frame_copy = screen.copy(); ox = random.randint(-shake, shake); oy = random.randint(-shake, shake)
            screen.fill(BLACK); screen.blit(frame_copy, (ox, oy)); shake -= 1

        present(); clock_u.tick(60)

    # ── 결과 ──
    if result == "win":
        WIN_DLG = [
            ("* Gah... I lost...?", 70),
            ("* I can't believe it.", 70),
            ("* But... you're really something, human.", 80),
            ("* The kind of human that doesn't give up.", 80),
            ("* ...", 60),
            ("* Don't you dare let this determination go to waste.", 90),
            ("* Do you understand me?", 75),
            ("* STAY DETERMINED.", 90),
        ]
        dead_u = pygame.transform.scale(UNDYNE_DEAD_IMAGE, (180, 180))
        shown_d2 = []; dlg_d2 = 0; lt2 = 0
        while dlg_d2 < len(WIN_DLG):
            for ev in poll_events():
                if ev.type == pygame.QUIT: pygame.quit(); return "quit"
                if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_SPACE, pygame.K_RETURN):
                    if dlg_d2 < len(WIN_DLG): shown_d2.append(WIN_DLG[dlg_d2][0]); dlg_d2 += 1; lt2 = 0
            lt2 += 1
            if dlg_d2 < len(WIN_DLG) and lt2 >= WIN_DLG[dlg_d2][1]:
                shown_d2.append(WIN_DLG[dlg_d2][0]); dlg_d2 += 1; lt2 = 0
            screen.fill((10, 10, 25))
            screen.blit(dead_u, (WIDTH // 2 - 90, HEIGHT // 2 - 170))
            bx3, by3, bw3, bh4 = WIDTH // 2 - 230, HEIGHT // 2 + 20, 460, 14 + min(len(shown_d2), 5) * 30 + 14
            pygame.draw.rect(screen, (15, 15, 40), (bx3, by3, bw3, bh4), border_radius=8)
            pygame.draw.rect(screen, (80, 160, 255), (bx3, by3, bw3, bh4), 2, border_radius=8)
            for i, msg in enumerate(shown_d2[-5:]):
                alpha3 = 255 if i == min(len(shown_d2), 5) - 1 else 120
                ts3 = small_font.render(msg, True, (180, 220, 255)); ts3.set_alpha(alpha3)
                screen.blit(ts3, (bx3 + 12, by3 + 10 + i * 30))
            adv3 = small_font.render("SPACE/ENTER : next", True, (80, 100, 130))
            screen.blit(adv3, (bx3 + bw3 - adv3.get_width() - 10, by3 + bh4 - 22))
            present(); clock_u.tick(60)
        ft = 120
        while ft > 0:
            for ev in poll_events():
                if ev.type == pygame.QUIT: pygame.quit(); return "quit"
                if ev.type == pygame.KEYDOWN: ft = 0
            screen.fill((10, 10, 25))
            screen.blit(dead_u, (WIDTH // 2 - 90, HEIGHT // 2 - 170))
            done_t = small_font.render("[Press any key]", True, (80, 160, 255))
            screen.blit(done_t, (WIDTH // 2 - done_t.get_width() // 2, HEIGHT // 2 + 30))
            if ft < 40:
                fd = pygame.Surface((WIDTH, HEIGHT)); fd.fill(BLACK)
                fd.set_alpha(int(255 * (1 - ft / 40))); screen.blit(fd, (0, 0))
            present(); clock_u.tick(60); ft -= 1
    else:
        et = 110
        while et > 0:
            for ev in poll_events():
                if ev.type == pygame.QUIT: pygame.quit(); return "quit"
                if ev.type == pygame.KEYDOWN: et = 0
            screen.fill(BLACK)
            msgs_l = [("* HUMAN! You were no match for me after all!", (180, 220, 255)),
                      ("", WHITE), ("YOU DIED", RED)]
            for i, (ln_l, col_l) in enumerate(msgs_l):
                ts_l = small_font.render(ln_l, True, col_l)
                screen.blit(ts_l, (WIDTH // 2 - ts_l.get_width() // 2, HEIGHT // 2 - 30 + i * 36))
            present(); clock_u.tick(60); et -= 1

    return result


def fight_sans(player, small_font):
    try:
        pygame.mixer.music.load("assets/sans_music.mp3")
        pygame.mixer.music.play(-1)
    except Exception:
        pass

    boss = SansBoss()
    clock_s = pygame.time.Clock()

    # Dialogue lines
    DIALOGUE = [
        "* heya.",
        "* you've been busy, huh?",
        "* welp.",
        "* i know what you're thinking.",
        "* 'this is all just a game.'",
        "* and i think that's the truth.",
        "* heh heh heh.",
        "* well, i'll be honest with you.",
        "* i've thought about it a lot.",
        "* and... to be honest...",
        "* i'm not ready to let you through.",
        "* so get ready.",
        "* cuz it's gonna be a bad time.",
    ]

    dlg_idx = 0
    sprite_s = pygame.transform.scale(SANS_IMAGE, (160, 160))
    dlg_running = True

    while dlg_running and dlg_idx < len(DIALOGUE):
        for ev in poll_events():
            if ev.type == pygame.QUIT:
                pygame.quit(); return "quit"
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    dlg_running = False
                elif ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z):
                    dlg_idx += 1

        screen.fill((10, 10, 20))
        screen.blit(sprite_s, (WIDTH // 5 - 80, HEIGHT // 2 - 80))

        box_x = WIDTH // 5 + 105
        box_y = HEIGHT // 2 - 80
        box_w = WIDTH - box_x - 30
        box_h = 170
        pygame.draw.rect(screen, (25, 25, 45), (box_x, box_y, box_w, box_h), border_radius=8)
        pygame.draw.rect(screen, (120, 120, 200), (box_x, box_y, box_w, box_h), 2, border_radius=8)

        shown = DIALOGUE[max(0, dlg_idx - 2): dlg_idx + 1]
        for i, line in enumerate(shown):
            alpha = 255 if i == len(shown) - 1 else 120
            lt = small_font.render(line, True, (alpha, alpha, alpha))
            screen.blit(lt, (box_x + 14, box_y + 14 + i * 26))

        adv = small_font.render("SPACE/ENTER : next", True, (160, 160, 180))
        skp = small_font.render("ESC : skip", True, (130, 130, 150))
        prog = small_font.render(f"{min(dlg_idx+1, len(DIALOGUE))}/{len(DIALOGUE)}", True, (90, 90, 110))
        screen.blit(adv, (box_x + 14, box_y + box_h - 42))
        screen.blit(skp, (box_x + box_w - skp.get_width() - 14, box_y + box_h - 42))
        screen.blit(prog, (box_x + box_w - prog.get_width() - 14, box_y + 10))

        present()
        clock_s.tick(60)

    # Battle starts immediately after dialogue
    player.max_hp = 40
    player.hp = 40
    result = "lose"
    shake = 0
    running = True
    heals_remaining = 3
    heal_flash = 0          # heal flash timer
    miss_timer = 0
    miss_x = 0
    miss_y = 0
    dash_evaluated = False  # 현재 대시에서 이미 판정했는지
    low_hp_triggered = False
    LOW_HP_THRESHOLD = 30   # trigger cutscene at 25% of 120

    GRAVITY_PATS = ("slam_gravity", "random_slams", "first_turn", "final_overdrive")

    def _fake_spare_cutscene():
        """거짓 자비: 대사 후 뼈 6개가 플레이어를 관통."""
        DLG = [
            ("* ...", 55),
            ("* heh heh heh.", 70),
            ("* did you really think", 65),
            ("* i'd let you off that easy?", 80),
            ("* you're gonna have a bad time.", 90),
        ]
        dlg_idx = 0
        dlg_timer = 0
        shown = []

        # ── 대사 단계 ──
        while dlg_idx < len(DLG):
            for ev in poll_events():
                if ev.type == pygame.QUIT:
                    pygame.quit(); return
                if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_SPACE, pygame.K_RETURN):
                    shown.append(DLG[dlg_idx][0])
                    dlg_idx += 1
                    dlg_timer = 0

            dlg_timer += 1
            if dlg_idx < len(DLG) and dlg_timer >= DLG[dlg_idx][1]:
                shown.append(DLG[dlg_idx][0])
                dlg_idx += 1
                dlg_timer = 0

            screen.fill((10, 10, 20))
            boss.draw(small_font)
            player.draw()

            # 제목
            title_s = pygame.font.SysFont(None, 48).render("FALSE MERCY", True, (255, 70, 70))
            screen.blit(title_s, (WIDTH // 2 - title_s.get_width() // 2, HEIGHT // 2 - 90))

            # 대사
            box_x = WIDTH // 2 - 200
            box_y = HEIGHT // 2 - 30
            pygame.draw.rect(screen, (18, 18, 35), (box_x, box_y, 400, 14 + len(shown) * 26 + 10),
                             border_radius=7)
            pygame.draw.rect(screen, (120, 80, 80), (box_x, box_y, 400, 14 + len(shown) * 26 + 10),
                             2, border_radius=7)
            for i, ln in enumerate(shown):
                alpha = 255 if i == len(shown) - 1 else 140
                lt = small_font.render(ln, True, (255, 220, 220))
                lt.set_alpha(alpha)
                screen.blit(lt, (box_x + 12, box_y + 10 + i * 26))

            present()
            clock_s.tick(60)

        # ── 뼈 6개 관통 단계 ──
        px, py = float(player.x), float(player.y)
        bones = []
        spawn_timer = 0
        spawned = 0
        MAX_B = 6

        while True:
            for ev in poll_events():
                if ev.type == pygame.QUIT:
                    pygame.quit(); return

            spawn_timer += 1
            if spawned < MAX_B and spawn_timer >= 16:
                spawn_timer = 0
                # 뼈를 Sans 위치에서 플레이어 방향으로 발사
                bx0 = float(boss.x)
                by0 = float(boss.y)
                # 약간 퍼지도록 랜덤 오프셋
                spread = (spawned - MAX_B // 2) * 22
                target_x = px + (0 if abs(bx0 - px) < 10 else 0)
                target_y = py + spread
                dx = target_x - bx0
                dy = target_y - by0
                dist = max(1.0, math.hypot(dx, dy))
                spd = 20.0
                bones.append({
                    "x": bx0, "y": by0,
                    "vx": dx / dist * spd,
                    "vy": dy / dist * spd,
                    "angle": math.atan2(dy, dx),
                    "alive": True,
                })
                spawned += 1

            for b in bones:
                if not b["alive"]: continue
                b["x"] += b["vx"]
                b["y"] += b["vy"]
                if (b["x"] < -120 or b["x"] > WIDTH + 120 or
                        b["y"] < -120 or b["y"] > HEIGHT + 120):
                    b["alive"] = False

            screen.fill((10, 10, 20))
            boss.draw(small_font)
            player.draw()

            # 제목 유지
            title_s2 = pygame.font.SysFont(None, 48).render("FALSE MERCY", True, (255, 70, 70))
            screen.blit(title_s2, (WIDTH // 2 - title_s2.get_width() // 2, HEIGHT // 2 - 90))

            # 뼈 그리기 (상세 bone shape)
            for b in bones:
                if not b["alive"]: continue
                blen = 55
                bw_b = 10
                angle = b["angle"]
                cx_b, cy_b = int(b["x"]), int(b["y"])
                ex_b = int(b["x"] + math.cos(angle) * blen)
                ey_b = int(b["y"] + math.sin(angle) * blen)
                # shaft
                pygame.draw.line(screen, WHITE, (cx_b, cy_b), (ex_b, ey_b), bw_b)
                # knobs at both ends
                pygame.draw.circle(screen, WHITE, (cx_b, cy_b - 5), bw_b // 2 + 3)
                pygame.draw.circle(screen, WHITE, (cx_b, cy_b + 5), bw_b // 2 + 3)
                pygame.draw.circle(screen, WHITE, (ex_b, ey_b - 5), bw_b // 2 + 3)
                pygame.draw.circle(screen, WHITE, (ex_b, ey_b + 5), bw_b // 2 + 3)
                # glow
                glow = pygame.Surface((20, 20), pygame.SRCALPHA)
                pygame.draw.circle(glow, (200, 200, 255, 60), (10, 10), 10)
                screen.blit(glow, (cx_b - 10, cy_b - 10))

            present()
            clock_s.tick(60)

            if spawned >= MAX_B and all(not b["alive"] for b in bones):
                break

        # 짧은 정지
        for _ in range(40):
            for ev in poll_events():
                if ev.type == pygame.QUIT:
                    pygame.quit(); return
            screen.fill((5, 5, 10))
            present()
            clock_s.tick(60)

    def _low_hp_cutscene():
        """Sans 저체력 컷신: 오른쪽 눈이 노랗게 빛나고 파란 불꽃."""
        sprite_big = pygame.transform.scale(SANS_IMAGE, (220, 220))
        flame_particles = []
        # Right eye position relative to sprite center
        eye_ox = int(220 * 0.58)   # 58% from left
        eye_oy = int(220 * 0.32)   # 32% from top
        sx = WIDTH // 2 - 110
        sy = HEIGHT // 2 - 110
        eye_gx = sx + eye_ox
        eye_gy = sy + eye_oy

        for frame in range(200):
            for ev in poll_events():
                if ev.type == pygame.QUIT:
                    pygame.quit(); return

            # Fade in
            alpha_bg = max(0, 220 - int(220 * frame / 30)) if frame < 30 else 0
            # Fade out at end
            if frame > 170:
                alpha_bg = int(255 * (frame - 170) / 30)

            screen.fill((5, 5, 15))
            screen.blit(sprite_big, (sx, sy))

            # Yellow glow (grows over first 40 frames)
            glow_r = min(18, int(18 * frame / 40)) if frame < 40 else 18
            if glow_r > 0:
                glow_surf = pygame.Surface((glow_r * 4, glow_r * 4), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (255, 220, 0, 100), (glow_r * 2, glow_r * 2), glow_r * 2)
                screen.blit(glow_surf, (eye_gx - glow_r * 2, eye_gy - glow_r * 2))
                pygame.draw.circle(screen, YELLOW, (eye_gx, eye_gy), glow_r)
                pygame.draw.circle(screen, WHITE, (eye_gx, eye_gy), max(1, glow_r // 3))

            # Blue flame particles from eye
            if frame > 15 and frame % 2 == 0:
                for _ in range(3):
                    flame_particles.append({
                        "x": float(eye_gx + random.randint(-6, 6)),
                        "y": float(eye_gy + random.randint(-4, 4)),
                        "vx": random.uniform(-0.8, 0.8),
                        "vy": random.uniform(-3.5, -1.0),
                        "life": random.randint(18, 35),
                        "max_life": 35,
                    })

            for fp in flame_particles:
                fp["x"] += fp["vx"]; fp["y"] += fp["vy"]; fp["life"] -= 1
                ratio = max(0, fp["life"] / fp["max_life"])
                r = max(1, int(9 * ratio))
                b_val = int(200 + 55 * ratio)
                g_val = int(160 * ratio)
                col_f = (int(30 * ratio), g_val, b_val, int(200 * ratio))
                fs = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                pygame.draw.circle(fs, col_f, (r, r), r)
                screen.blit(fs, (int(fp["x"]) - r, int(fp["y"]) - r))
            flame_particles = [fp for fp in flame_particles if fp["life"] > 0]

            # Dialogue
            if frame > 30:
                line1 = small_font.render("* heh...", True, WHITE)
                screen.blit(line1, (WIDTH // 2 - line1.get_width() // 2, HEIGHT // 2 + 125))
            if frame > 80:
                line2 = small_font.render("* you're really something else.", True, (220, 220, 220))
                screen.blit(line2, (WIDTH // 2 - line2.get_width() // 2, HEIGHT // 2 + 150))
            if frame > 130:
                line3 = small_font.render("* don't say i didn't warn ya.", True, YELLOW)
                screen.blit(line3, (WIDTH // 2 - line3.get_width() // 2, HEIGHT // 2 + 175))

            # Fade overlay
            if alpha_bg > 0:
                fade_s = pygame.Surface((WIDTH, HEIGHT))
                fade_s.fill(BLACK)
                fade_s.set_alpha(alpha_bg)
                screen.blit(fade_s, (0, 0))

            present()
            clock_s.tick(60)

    while running:
        for event in poll_events():
            if event.type == pygame.QUIT:
                pygame.quit(); return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False; result = "lose"
                elif event.key == pygame.K_SPACE:
                    player.try_dash()
                elif event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                    if heals_remaining > 0:
                        player.hp = player.max_hp
                        heals_remaining -= 1
                        heal_flash = 35
                elif event.key == pygame.K_e:
                    player.try_heal()

        keys = pygame.key.get_pressed()
        player.handle_move(keys)
        player.update()

        boss.update(player)

        # 대시가 끝나면 판정 초기화
        if not player.dashing:
            dash_evaluated = False

        # Dash attack on boss (20% miss chance) — 대시 1회당 1번만 판정
        if player.dashing and not dash_evaluated and boss.get_rect().colliderect(player.get_rect()):
            dash_evaluated = True
            if boss.pattern != "spare" and boss.is_vulnerable():
                if random.random() < 0.20:
                    miss_timer = 45
                    miss_x = int(boss.x)
                    miss_y = int(boss.y) - 40
                else:
                    boss.take_damage(2)
                    shake = max(shake, 6)

        # Spare logic
        if boss.pattern == "spare" and boss.state == "active":
            if keys[pygame.K_SPACE] or keys[pygame.K_RETURN]:
                boss.data["attacked"] = True
            if player.dashing and boss.get_rect().colliderect(player.get_rect()):
                boss.data["attacked"] = True
            if boss.data["spare_timer"] <= 0 and not boss.data["attacked"]:
                _fake_spare_cutscene()
                player.hp = 0

        if (boss.pattern == "spare" and boss.state == "active"
                and boss.data.get("attacked")):
            boss.state = "vulnerable"
            boss.timer = 18

        # Low HP cutscene (once)
        if not low_hp_triggered and boss.hp <= LOW_HP_THRESHOLD and boss.hp > 0:
            low_hp_triggered = True
            _low_hp_cutscene()

        if player.hp <= 0:
            result = "lose"; running = False
        elif boss.hp <= 0:
            result = "win"; running = False

        # ── Draw ──
        screen.fill((10, 10, 20))
        boss.draw(small_font)

        # Gravity attack: player turns dark blue
        in_gravity = (boss.pattern in GRAVITY_PATS and boss.state == "active")
        if in_gravity and not player.dashing:
            orig_rect = player.get_rect()
            pygame.draw.rect(screen, (20, 20, 160), orig_rect)
            if player.hit_cooldown > 0 and player.hit_cooldown % 10 < 5:
                pygame.draw.rect(screen, (100, 100, 255), orig_rect, 2)
            if player.bound_timer > 0:
                cx_p, cy_p = int(player.x), int(player.y + player.size // 2 + 8)
                pygame.draw.circle(screen, PURPLE, (cx_p, cy_p), 10, 2)
        else:
            player.draw()

        # Heal flash overlay
        if heal_flash > 0:
            hf_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            hf_alpha = int(120 * heal_flash / 35)
            hf_surf.fill((0, 255, 100, hf_alpha))
            screen.blit(hf_surf, (0, 0))
            hf_msg = small_font.render(f"HEAL! ({heals_remaining} left)", True, (0, 255, 150))
            screen.blit(hf_msg, (WIDTH // 2 - hf_msg.get_width() // 2, HEIGHT // 2 - 20))
            heal_flash -= 1

        # MISS text
        if miss_timer > 0:
            m_alpha = min(255, miss_timer * 5)
            m_surf = pygame.font.SysFont(None, 52).render("MISS", True, (255, 240, 60))
            m_surf.set_alpha(m_alpha)
            screen.blit(m_surf, (miss_x - m_surf.get_width() // 2,
                                  miss_y - (45 - miss_timer) // 2))
            miss_timer -= 1

        # Turn counter
        turn_txt = small_font.render(f"Turn {boss.turn}/13", True, (200, 200, 200))
        screen.blit(turn_txt, (WIDTH - turn_txt.get_width() - 12, 14))

        # Heal uses counter
        heal_col = (100, 255, 150) if heals_remaining > 0 else (100, 100, 100)
        heal_txt = small_font.render(f"SHIFT Heal: {heals_remaining}/3", True, heal_col)
        screen.blit(heal_txt, (12, 14))

        # Player HP bar + heal indicator (bottom-left)
        _phb_w = 160
        pygame.draw.rect(screen, (50, 50, 50), (12, HEIGHT - 32, _phb_w, 14))
        pygame.draw.rect(screen, (80, 220, 80),
                         (12, HEIGHT - 32, int(_phb_w * max(player.hp, 0) / player.max_hp), 14))
        _php_t = small_font.render(f"HP {player.hp}/{player.max_hp}", True, (180, 255, 180))
        screen.blit(_php_t, (12, HEIGHT - 50))
        _hcd_s = player.heal_cooldown
        _hcol_s = (80, 255, 150) if _hcd_s == 0 else (120, 120, 120)
        _hw_s = _phb_w - int(_phb_w * _hcd_s / player.HEAL_MAX_CD)
        pygame.draw.rect(screen, (30, 60, 30), (12, HEIGHT - 62, _phb_w, 8))
        pygame.draw.rect(screen, _hcol_s,      (12, HEIGHT - 62, _hw_s, 8))
        _hlbl_s = "E: 회복 [준비됨]" if _hcd_s == 0 else f"E: 회복 ({_hcd_s // 60 + 1}s)"
        screen.blit(small_font.render(_hlbl_s, True, _hcol_s), (12, HEIGHT - 78))

        # Screen shake
        if shake > 0:
            frame_copy = screen.copy()
            ox = random.randint(-shake, shake)
            oy = random.randint(-shake, shake)
            screen.fill(BLACK)
            screen.blit(frame_copy, (ox, oy))
            shake -= 1

        present()
        clock_s.tick(60)

    # Result screen
    if result == "win":
        DEATH_LINES = [
            ("* welp.",                                       WHITE,           80),
            ("* i'm going to sleep.",                         WHITE,           80),
            ("* good night.",                                 WHITE,           80),
            ("* z z z ...",                                   (180, 180, 220), 110),
            ("* hey, don't forget...",                        (200, 200, 200), 90),
            ("* stay determined.",                            YELLOW,          90),
            ("* you're gonna carry that weight.",             (200, 200, 200), 90),
            ("* ...",                                         WHITE,           70),
            ("* see ya.",                                     (180, 180, 220), 100),
        ]

        dead_img = pygame.transform.scale(SANS_DEAD_IMAGE, (380, 265))
        dlg_d = 0          # current line index
        line_timer = 0     # auto-advance timer
        shown_lines = []   # lines revealed so far

        while dlg_d < len(DEATH_LINES):
            for ev in poll_events():
                if ev.type == pygame.QUIT:
                    pygame.quit(); return "quit"
                if ev.type == pygame.KEYDOWN:
                    if ev.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_z):
                        if dlg_d < len(DEATH_LINES):
                            shown_lines.append(DEATH_LINES[dlg_d])
                            dlg_d += 1
                            line_timer = 0

            line_timer += 1
            if dlg_d < len(DEATH_LINES) and line_timer >= DEATH_LINES[dlg_d][2]:
                shown_lines.append(DEATH_LINES[dlg_d])
                dlg_d += 1
                line_timer = 0

            # Draw
            screen.fill((10, 10, 20))
            screen.blit(dead_img, (WIDTH // 2 - 190, HEIGHT // 2 - 220))

            # Dialogue box
            box_x = WIDTH // 2 - 190
            box_y = HEIGHT // 2 + 55
            box_w = 380
            box_h = 14 + min(len(shown_lines), 5) * 26 + 28
            pygame.draw.rect(screen, (18, 18, 35),
                             (box_x, box_y, box_w, box_h), border_radius=8)
            pygame.draw.rect(screen, (100, 100, 180),
                             (box_x, box_y, box_w, box_h), 2, border_radius=8)

            visible = shown_lines[-5:]
            for i, (msg, col_t, _) in enumerate(visible):
                alpha = 255 if i == len(visible) - 1 else 130
                surf_t = small_font.render(msg, True, col_t)
                surf_t.set_alpha(alpha)
                screen.blit(surf_t, (box_x + 12, box_y + 10 + i * 26))

            hint = small_font.render("SPACE / ENTER : next", True, (100, 100, 120))
            screen.blit(hint, (box_x + box_w - hint.get_width() - 10,
                               box_y + box_h - 22))

            present()
            clock_s.tick(60)

        # Final pause after all lines
        final_t = 160
        while final_t > 0:
            for ev in poll_events():
                if ev.type == pygame.QUIT:
                    pygame.quit(); return "quit"
                if ev.type == pygame.KEYDOWN:
                    final_t = 0
            screen.fill((10, 10, 20))
            screen.blit(dead_img, (WIDTH // 2 - 190, HEIGHT // 2 - 220))
            box_x2 = WIDTH // 2 - 190
            box_y2 = HEIGHT // 2 + 55
            box_w2 = 380
            box_h2 = 14 + min(len(shown_lines), 5) * 26 + 28
            pygame.draw.rect(screen, (18, 18, 35),
                             (box_x2, box_y2, box_w2, box_h2), border_radius=8)
            pygame.draw.rect(screen, (100, 100, 180),
                             (box_x2, box_y2, box_w2, box_h2), 2, border_radius=8)
            for i, (msg, col_t, _) in enumerate(shown_lines[-5:]):
                alpha = 255 if i == len(shown_lines[-5:]) - 1 else 130
                surf_t = small_font.render(msg, True, col_t)
                surf_t.set_alpha(alpha)
                screen.blit(surf_t, (box_x2 + 12, box_y2 + 10 + i * 26))
            done_t = small_font.render("[Press any key]", True, YELLOW)
            screen.blit(done_t, (WIDTH // 2 - done_t.get_width() // 2,
                                 box_y2 + box_h2 + 10))

            # Fade to black at the end
            if final_t < 40:
                fade_s = pygame.Surface((WIDTH, HEIGHT))
                fade_s.fill(BLACK)
                fade_s.set_alpha(int(255 * (1 - final_t / 40)))
                screen.blit(fade_s, (0, 0))

            present()
            clock_s.tick(60)
            final_t -= 1
    else:
        end_timer = 120
        while end_timer > 0:
            for ev in poll_events():
                if ev.type == pygame.QUIT:
                    pygame.quit(); return "quit"
                if ev.type == pygame.KEYDOWN:
                    end_timer = 0
            screen.fill(BLACK)
            lose_msgs = [
                ("* but nobody came.", (180, 180, 180)),
                ("", WHITE),
                ("YOU DIED", RED),
            ]
            for i, (ln, col_t2) in enumerate(lose_msgs):
                ts2 = small_font.render(ln, True, col_t2)
                screen.blit(ts2, (WIDTH // 2 - ts2.get_width() // 2, HEIGHT // 2 - 30 + i * 36))
            present()
            clock_s.tick(60)
            end_timer -= 1

    return result


def fight_toriel(player, small_font):
    try:
        pygame.mixer.music.load("assets/boss_music.mp3")
        pygame.mixer.music.play(-1)
    except Exception:
        pass

    boss = TorielBoss()
    clock_t = pygame.time.Clock()

    INTRO = [
        "* Oh my, a human child...",
        "* I am Toriel, caretaker of the Ruins.",
        "* I have lived here for a long, long time...",
        "* And I have taken care of many children just like you.",
        "* But if you insist on leaving...",
        "* I must test whether you are truly ready for the world beyond.",
        "* Do not worry. I will not hurt you more than necessary.",
    ]
    sprite_t = pygame.transform.scale(TORIEL_IMAGE, (120, 140))
    dlg_idx = 0; dlg_running = True
    while dlg_running and dlg_idx < len(INTRO):
        for ev in poll_events():
            if ev.type == pygame.QUIT: pygame.quit(); return "quit"
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE: dlg_running = False
                elif ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z): dlg_idx += 1
        screen.fill((15, 5, 25))
        screen.blit(sprite_t, (WIDTH * 3 // 4 - 60, HEIGHT // 2 - 70))
        bx, by, bw, bh2 = 30, HEIGHT // 2 - 110, WIDTH * 3 // 4 - 60, 230
        pygame.draw.rect(screen, (20, 10, 30), (bx, by, bw, bh2), border_radius=8)
        pygame.draw.rect(screen, (255, 160, 60), (bx, by, bw, bh2), 2, border_radius=8)
        shown = INTRO[max(0, dlg_idx - 3): dlg_idx + 1]
        for i, ln in enumerate(shown):
            alpha = 255 if i == len(shown) - 1 else 110
            lt = small_font.render(ln, True, (255, 220, 150)); lt.set_alpha(alpha)
            screen.blit(lt, (bx + 14, by + 14 + i * 38))
        adv = small_font.render("SPACE/ENTER : next   ESC : skip", True, (150, 100, 80))
        screen.blit(adv, (bx + 14, by + bh2 - 26))
        present(); clock_t.tick(60)

    player.max_hp = 25; player.hp = 25
    result = "lose"; shake = 0; running = True
    dash_evaluated = False
    mid_dlg_done = set()

    MID_DLG = {
        75: ["* Hm? You are... quite determined.", "* Please, stop this before someone gets hurt."],
        50: ["* You are hurting me, my child.", "* Is this truly what you want?"],
        25: ["* ...I see.", "* You have made up your mind.", "* Then I will do the same."],
    }

    def _show_mid_dlg(lines):
        t = 180
        while t > 0:
            for ev in poll_events():
                if ev.type == pygame.QUIT: pygame.quit(); return
                if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_SPACE, pygame.K_RETURN):
                    t = 0
            screen.fill((15, 5, 25))
            boss.draw(small_font, mercy_active=(player.hp <= 1))
            bx2, by2 = WIDTH // 2 - 240, HEIGHT // 2 + 40
            bw2, bh3 = 480, 20 + len(lines) * 32
            pygame.draw.rect(screen, (20, 10, 30), (bx2, by2, bw2, bh3), border_radius=7)
            pygame.draw.rect(screen, (255, 160, 60), (bx2, by2, bw2, bh3), 2, border_radius=7)
            for i, ln in enumerate(lines):
                lt2 = small_font.render(ln, True, (255, 220, 150))
                screen.blit(lt2, (bx2 + 12, by2 + 10 + i * 32))
            present(); clock_t.tick(60); t -= 1

    while running:
        for event in poll_events():
            if event.type == pygame.QUIT: pygame.quit(); return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: running = False; result = "lose"
                elif event.key == pygame.K_SPACE: player.try_dash()
                elif event.key == pygame.K_e:     player.try_heal()

        if not player.dashing and player.bound_timer <= 0:
            keys = pygame.key.get_pressed()
            dx = dy = 0
            if keys[pygame.K_a]: dx -= 1
            if keys[pygame.K_d]: dx += 1
            if keys[pygame.K_w]: dy -= 1
            if keys[pygame.K_s]: dy += 1
            if dx or dy:
                length = math.hypot(dx, dy)
                dx, dy = dx / length, dy / length
                player.facing = (dx, dy)
                player.x = max(player.size, min(WIDTH - player.size, player.x + dx * player.speed))
                player.y = max(player.size, min(HEIGHT - player.size, player.y + dy * player.speed))
        player.update()

        if not player.dashing:
            dash_evaluated = False
        if (player.dashing and not dash_evaluated
                and boss.get_rect().colliderect(player.get_rect())):
            dash_evaluated = True
            if boss.is_vulnerable():
                boss.take_damage(2); shake = max(shake, 5)

        mercy_now = player.hp <= 1
        boss.update(player)

        hp_pct = int(boss.hp / boss.max_hp * 100)
        for threshold, lines in MID_DLG.items():
            if threshold not in mid_dlg_done and hp_pct <= threshold:
                mid_dlg_done.add(threshold)
                _show_mid_dlg(lines)

        if player.hp <= 0: result = "lose"; running = False
        elif boss.hp <= 0: result = "win"; running = False

        screen.fill((15, 5, 25))
        boss.draw(small_font, mercy_active=mercy_now)
        player.draw()

        _phb_w = 160
        pygame.draw.rect(screen, (50, 50, 50), (12, HEIGHT - 32, _phb_w, 14))
        hp_ratio = max(player.hp, 0) / player.max_hp
        pygame.draw.rect(screen, (80, 220, 80), (12, HEIGHT - 32, int(_phb_w * hp_ratio), 14))
        _php_t = small_font.render(f"HP {player.hp}/{player.max_hp}", True, (180, 255, 180))
        screen.blit(_php_t, (12, HEIGHT - 50))
        _hcd_t = player.heal_cooldown
        _hcol_t = (80, 255, 150) if _hcd_t == 0 else (120, 120, 120)
        _hw_t = _phb_w - int(_phb_w * _hcd_t / player.HEAL_MAX_CD)
        pygame.draw.rect(screen, (30, 60, 30), (12, HEIGHT - 62, _phb_w, 8))
        pygame.draw.rect(screen, _hcol_t,      (12, HEIGHT - 62, _hw_t, 8))
        _hlbl_t = "E: 회복 [준비됨]" if _hcd_t == 0 else f"E: 회복 ({_hcd_t // 60 + 1}s)"
        screen.blit(small_font.render(_hlbl_t, True, _hcol_t), (12, HEIGHT - 78))

        turn_txt = small_font.render(f"Turn {boss.turn}/{len(boss.TURN_SEQ)}", True, (200, 200, 200))
        screen.blit(turn_txt, (WIDTH - turn_txt.get_width() - 12, 14))

        if shake > 0:
            frame_copy = screen.copy()
            ox = random.randint(-shake, shake); oy = random.randint(-shake, shake)
            screen.fill(BLACK); screen.blit(frame_copy, (ox, oy)); shake -= 1

        present(); clock_t.tick(60)

    if result == "win":
        WIN_DLG = [
            ("* ...", 50),
            ("* You are... very strong, my child.", 80),
            ("* I am sorry I could not protect you better.", 90),
            ("* Please... please be careful out there.", 90),
            ("* The world beyond these Ruins... it is dangerous.", 90),
            ("* But I believe you can handle it.", 80),
            ("* Take care of yourself.", 80),
            ("* ...I am proud of you.", 100),
        ]
        dead_t = pygame.transform.scale(TORIEL_DEAD_IMAGE, (90, 160))
        shown_d = []; dlg_d = 0; lt2 = 0
        while dlg_d < len(WIN_DLG):
            for ev in poll_events():
                if ev.type == pygame.QUIT: pygame.quit(); return "quit"
                if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_SPACE, pygame.K_RETURN):
                    if dlg_d < len(WIN_DLG):
                        shown_d.append(WIN_DLG[dlg_d][0]); dlg_d += 1; lt2 = 0
            lt2 += 1
            if dlg_d < len(WIN_DLG) and lt2 >= WIN_DLG[dlg_d][1]:
                shown_d.append(WIN_DLG[dlg_d][0]); dlg_d += 1; lt2 = 0
            screen.fill((15, 5, 25))
            screen.blit(dead_t, (WIDTH // 2 - 45, HEIGHT // 2 - 180))
            bx3, by3 = WIDTH // 2 - 240, HEIGHT // 2 + 10
            bw3, bh4 = 480, 14 + min(len(shown_d), 5) * 30 + 14
            pygame.draw.rect(screen, (20, 10, 30), (bx3, by3, bw3, bh4), border_radius=8)
            pygame.draw.rect(screen, (255, 160, 60), (bx3, by3, bw3, bh4), 2, border_radius=8)
            for i, msg in enumerate(shown_d[-5:]):
                alpha3 = 255 if i == min(len(shown_d), 5) - 1 else 120
                ts3 = small_font.render(msg, True, (255, 220, 150)); ts3.set_alpha(alpha3)
                screen.blit(ts3, (bx3 + 12, by3 + 10 + i * 30))
            adv3 = small_font.render("SPACE/ENTER : next", True, (130, 80, 60))
            screen.blit(adv3, (bx3 + bw3 - adv3.get_width() - 10, by3 + bh4 - 22))
            present(); clock_t.tick(60)
        ft = 120
        while ft > 0:
            for ev in poll_events():
                if ev.type == pygame.QUIT: pygame.quit(); return "quit"
                if ev.type == pygame.KEYDOWN: ft = 0
            screen.fill((15, 5, 25))
            screen.blit(dead_t, (WIDTH // 2 - 45, HEIGHT // 2 - 180))
            done_t2 = small_font.render("[Press any key]", True, (255, 160, 60))
            screen.blit(done_t2, (WIDTH // 2 - done_t2.get_width() // 2, HEIGHT // 2 + 30))
            if ft < 40:
                fd = pygame.Surface((WIDTH, HEIGHT)); fd.fill(BLACK)
                fd.set_alpha(int(255 * (1 - ft / 40))); screen.blit(fd, (0, 0))
            present(); clock_t.tick(60); ft -= 1
    else:
        end_timer = 180
        while end_timer > 0:
            for ev in poll_events():
                if ev.type == pygame.QUIT: pygame.quit(); return "quit"
                if ev.type == pygame.KEYDOWN: end_timer = 0
            screen.fill(BLACK)
            lose_msgs = [
                ("* Do not worry, my child.", (255, 200, 120)),
                ("* This is not the end.", (255, 200, 120)),
                ("", WHITE),
                ("YOU DIED", RED),
            ]
            for i, (ln, col_t2) in enumerate(lose_msgs):
                ts2 = small_font.render(ln, True, col_t2)
                screen.blit(ts2, (WIDTH // 2 - ts2.get_width() // 2, HEIGHT // 2 - 30 + i * 36))
            present()
            clock_t.tick(60)
            end_timer -= 1

    return result


def fight_asriel(player, small_font):
    try:
        pygame.mixer.music.load("assets/boss_music.mp3")
        pygame.mixer.music.play(-1)
    except Exception:
        pass

    boss = AsrielBoss()
    clock_a = pygame.time.Clock()

    # ── 인트로 대사 ──
    INTRO = [
        "* ...it's been a while, human.",
        "* I'm not who I used to be anymore.",
        "* The power of six souls, and Chara's power too...",
        "* I have become the God of Hyperdeath.",
        "* With this power... I can do anything.",
        "* Come on then, human.",
        "* Let me show you the end of this world!",
    ]
    sprite_a = pygame.transform.scale(ASRIEL_IMAGE, (190, 190))
    dlg_idx = 0
    dlg_running = True
    while dlg_running and dlg_idx < len(INTRO):
        for ev in poll_events():
            if ev.type == pygame.QUIT:
                pygame.quit(); return "quit"
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    dlg_running = False
                elif ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z):
                    dlg_idx += 1

        screen.fill((8, 8, 20))
        screen.blit(sprite_a, (WIDTH // 5 - 95, HEIGHT // 2 - 95))

        box_x = WIDTH // 5 + 100
        box_y = HEIGHT // 2 - 80
        box_w = WIDTH - box_x - 30
        box_h = 170
        pygame.draw.rect(screen, (25, 20, 45), (box_x, box_y, box_w, box_h), border_radius=8)
        pygame.draw.rect(screen, (200, 160, 255), (box_x, box_y, box_w, box_h), 2, border_radius=8)

        shown = INTRO[max(0, dlg_idx - 2): dlg_idx + 1]
        for i, line in enumerate(shown):
            alpha = 255 if i == len(shown) - 1 else 120
            lt = small_font.render(line, True, (alpha, alpha, alpha))
            screen.blit(lt, (box_x + 14, box_y + 14 + i * 26))

        adv = small_font.render("SPACE/ENTER : next", True, (160, 160, 180))
        skp = small_font.render("ESC : skip", True, (130, 130, 150))
        prog = small_font.render(f"{min(dlg_idx+1, len(INTRO))}/{len(INTRO)}", True, (90, 90, 110))
        screen.blit(adv, (box_x + 14, box_y + box_h - 42))
        screen.blit(skp, (box_x + box_w - skp.get_width() - 14, box_y + box_h - 42))
        screen.blit(prog, (box_x + box_w - prog.get_width() - 14, box_y + 10))

        present()
        clock_a.tick(60)

    # ── 전투 ──
    player.max_hp = 30
    player.hp = 30
    result = "lose"
    shake = 0
    running = True
    dash_evaluated = False
    mid_dlg_done = set()

    MID_DLG = {
        70: ["* Not bad, human.", "* But that's nowhere near enough!"],
        35: ["* Grr... to think you'd push me this far.", "* Fine. Let me show you a bit more of my true power."],
    }

    def _show_dlg_box(lines):
        t = 170
        while t > 0:
            for ev in poll_events():
                if ev.type == pygame.QUIT:
                    pygame.quit(); return
                if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_SPACE, pygame.K_RETURN):
                    t = 0
            screen.fill((8, 8, 20))
            boss.draw(small_font)
            bx2, by2 = WIDTH // 2 - 230, HEIGHT // 2 + 40
            bw2, bh2 = 460, 20 + len(lines) * 32
            pygame.draw.rect(screen, (18, 15, 35), (bx2, by2, bw2, bh2), border_radius=7)
            pygame.draw.rect(screen, (200, 160, 255), (bx2, by2, bw2, bh2), 2, border_radius=7)
            for i, ln in enumerate(lines):
                lt2 = small_font.render(ln, True, (230, 210, 255))
                screen.blit(lt2, (bx2 + 12, by2 + 10 + i * 32))
            present(); clock_a.tick(60); t -= 1

    def _phase2_awaken_cutscene():
        """2페이즈(절대신) 각성 연출과 대사."""
        LINES = [
            "* ...heh heh heh.",
            "* Did you really think that was enough to stop me?",
            "* Now, let me show you...",
            "* the absolute power of a god!",
        ]
        for frame in range(150):
            for ev in poll_events():
                if ev.type == pygame.QUIT:
                    pygame.quit(); return
            screen.fill((5, 5, 15))
            glow_r = min(240, frame * 3)
            gs = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.circle(gs, (255, 255, 255, max(0, 90 - frame)),
                               (int(boss.x), int(boss.y)), glow_r)
            screen.blit(gs, (0, 0))
            boss.draw(small_font)
            present(); clock_a.tick(60)

        dlg_idx2 = 0; timer2 = 0; shown2 = []
        while dlg_idx2 < len(LINES):
            for ev in poll_events():
                if ev.type == pygame.QUIT:
                    pygame.quit(); return
                if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_SPACE, pygame.K_RETURN):
                    shown2.append(LINES[dlg_idx2]); dlg_idx2 += 1; timer2 = 0
            timer2 += 1
            if dlg_idx2 < len(LINES) and timer2 >= 75:
                shown2.append(LINES[dlg_idx2]); dlg_idx2 += 1; timer2 = 0

            screen.fill((5, 5, 15))
            boss.draw(small_font)
            box3_x, box3_y = WIDTH // 2 - 220, HEIGHT // 2 + 60
            box3_w, box3_h = 440, 14 + min(len(shown2), 4) * 32 + 10
            pygame.draw.rect(screen, (18, 15, 35), (box3_x, box3_y, box3_w, box3_h), border_radius=7)
            pygame.draw.rect(screen, (200, 160, 255), (box3_x, box3_y, box3_w, box3_h), 2, border_radius=7)
            for i, ln3 in enumerate(shown2[-4:]):
                alpha3 = 255 if i == min(len(shown2), 4) - 1 else 120
                lt3 = small_font.render(ln3, True, (230, 210, 255))
                lt3.set_alpha(alpha3)
                screen.blit(lt3, (box3_x + 12, box3_y + 10 + i * 32))
            present(); clock_a.tick(60)

    while running:
        for event in poll_events():
            if event.type == pygame.QUIT:
                pygame.quit(); return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False; result = "lose"
                elif event.key == pygame.K_SPACE:
                    player.try_dash()
                elif event.key == pygame.K_e:
                    player.try_heal()

        keys = pygame.key.get_pressed()
        player.handle_move(keys)
        player.update()

        was_phase2 = boss.phase2
        boss.update(player)

        if not player.dashing:
            dash_evaluated = False
        if (player.dashing and not dash_evaluated
                and boss.get_rect().colliderect(player.get_rect())):
            dash_evaluated = True
            if boss.pattern == "save_window" and boss.state == "active":
                boss.saved = True
            elif boss.is_vulnerable():
                boss.take_damage(2); shake = max(shake, 6)

        if boss.phase2 and not was_phase2:
            _phase2_awaken_cutscene()

        if not boss.phase2:
            hp_pct = int(boss.hp / boss.max_hp * 100)
            for threshold, lines in MID_DLG.items():
                if threshold not in mid_dlg_done and hp_pct <= threshold:
                    mid_dlg_done.add(threshold)
                    _show_dlg_box(lines)

        if player.hp <= 0:
            result = "lose"; running = False
        elif boss.saved:
            result = "win"; running = False

        # ── 그리기 ──
        screen.fill((8, 8, 20))
        boss.draw(small_font)
        player.draw()

        if boss.pattern == "save_window" and boss.state == "active":
            save_t = small_font.render("Dash (SPACE) into Asriel to SAVE him!", True, (255, 255, 180))
            screen.blit(save_t, (WIDTH // 2 - save_t.get_width() // 2, HEIGHT - 78))

        _phb_w = 160
        pygame.draw.rect(screen, (50, 50, 50), (12, HEIGHT - 32, _phb_w, 14))
        pygame.draw.rect(screen, (80, 220, 80),
                         (12, HEIGHT - 32, int(_phb_w * max(player.hp, 0) / player.max_hp), 14))
        _php_t = small_font.render(f"HP {player.hp}/{player.max_hp}", True, (180, 255, 180))
        screen.blit(_php_t, (12, HEIGHT - 50))
        _hcd_a = player.heal_cooldown
        _hcol_a = (80, 255, 150) if _hcd_a == 0 else (120, 120, 120)
        _hw_a = _phb_w - int(_phb_w * _hcd_a / player.HEAL_MAX_CD)
        pygame.draw.rect(screen, (30, 60, 30), (12, HEIGHT - 62, _phb_w, 8))
        pygame.draw.rect(screen, _hcol_a,      (12, HEIGHT - 62, _hw_a, 8))
        _hlbl_a = "E: 회복 [준비됨]" if _hcd_a == 0 else f"E: 회복 ({_hcd_a // 60 + 1}s)"
        screen.blit(small_font.render(_hlbl_a, True, _hcol_a), (12, HEIGHT - 78))

        phase_txt = "PHASE 1" if not boss.phase2 else "PHASE 2"
        pt_s = small_font.render(phase_txt, True, (200, 200, 200))
        screen.blit(pt_s, (WIDTH - pt_s.get_width() - 12, 14))

        if shake > 0:
            frame_copy = screen.copy()
            ox = random.randint(-shake, shake); oy = random.randint(-shake, shake)
            screen.fill(BLACK); screen.blit(frame_copy, (ox, oy)); shake -= 1

        present()
        clock_a.tick(60)

    # ── 결과 ──
    if result == "win":
        WIN_DLG = [
            ("* ...thank you.", 70),
            ("* For saving me.", 75),
            ("* I can finally go back to who I really am.", 85),
            ("* I don't have to carry everyone's hearts anymore.", 85),
            ("* I'm just... an ordinary goat kid now.", 90),
            ("* ...thank you, my oldest friend.", 90),
            ("* Goodbye, human.", 80),
        ]
        returned_img = pygame.transform.scale(ASRIEL_RETURNED_IMAGE, (170, 96))
        shown_d, dlg_d, lt_ = [], 0, 0
        while dlg_d < len(WIN_DLG):
            for ev in poll_events():
                if ev.type == pygame.QUIT:
                    pygame.quit(); return "quit"
                if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_SPACE, pygame.K_RETURN):
                    if dlg_d < len(WIN_DLG):
                        shown_d.append(WIN_DLG[dlg_d][0]); dlg_d += 1; lt_ = 0
            lt_ += 1
            if dlg_d < len(WIN_DLG) and lt_ >= WIN_DLG[dlg_d][1]:
                shown_d.append(WIN_DLG[dlg_d][0]); dlg_d += 1; lt_ = 0

            screen.fill((10, 10, 25))
            screen.blit(returned_img, (WIDTH // 2 - 85, HEIGHT // 2 - 150))
            bx3, by3 = WIDTH // 2 - 230, HEIGHT // 2 + 10
            bw3, bh3 = 460, 14 + min(len(shown_d), 5) * 30 + 14
            pygame.draw.rect(screen, (15, 15, 40), (bx3, by3, bw3, bh3), border_radius=8)
            pygame.draw.rect(screen, (200, 160, 255), (bx3, by3, bw3, bh3), 2, border_radius=8)
            for i, msg in enumerate(shown_d[-5:]):
                alpha3 = 255 if i == min(len(shown_d), 5) - 1 else 120
                ts3 = small_font.render(msg, True, (230, 210, 255))
                ts3.set_alpha(alpha3)
                screen.blit(ts3, (bx3 + 12, by3 + 10 + i * 30))
            adv3 = small_font.render("SPACE/ENTER : next", True, (140, 110, 170))
            screen.blit(adv3, (bx3 + bw3 - adv3.get_width() - 10, by3 + bh3 - 22))
            present(); clock_a.tick(60)

        ft = 140
        while ft > 0:
            for ev in poll_events():
                if ev.type == pygame.QUIT:
                    pygame.quit(); return "quit"
                if ev.type == pygame.KEYDOWN:
                    ft = 0
            screen.fill((10, 10, 25))
            screen.blit(returned_img, (WIDTH // 2 - 85, HEIGHT // 2 - 150))
            done_t = small_font.render("SAVED", True, (255, 240, 180))
            screen.blit(done_t, (WIDTH // 2 - done_t.get_width() // 2, HEIGHT // 2 + 20))
            done_t2 = small_font.render("[Press any key]", True, (200, 160, 255))
            screen.blit(done_t2, (WIDTH // 2 - done_t2.get_width() // 2, HEIGHT // 2 + 50))
            if ft < 40:
                fd = pygame.Surface((WIDTH, HEIGHT)); fd.fill(BLACK)
                fd.set_alpha(int(255 * (1 - ft / 40))); screen.blit(fd, (0, 0))
            present(); clock_a.tick(60); ft -= 1
    else:
        end_timer = 150
        while end_timer > 0:
            for ev in poll_events():
                if ev.type == pygame.QUIT:
                    pygame.quit(); return "quit"
                if ev.type == pygame.KEYDOWN:
                    end_timer = 0
            screen.fill(BLACK)
            lose_msgs = [
                ("* ...you're still not strong enough.", (220, 190, 255)),
                ("", WHITE),
                ("YOU DIED", RED),
            ]
            for i, (ln, col_l) in enumerate(lose_msgs):
                ts_l = small_font.render(ln, True, col_l)
                screen.blit(ts_l, (WIDTH // 2 - ts_l.get_width() // 2, HEIGHT // 2 - 30 + i * 36))
            present(); clock_a.tick(60); end_timer -= 1

    return result


def run_single_boss(boss_cls):
    """보스 선택 모드에서 특정 보스 하나와 싸운다."""
    player = BossPlayer()
    small_font = pygame.font.SysFont(None, 28)

    if boss_cls == "SansBoss":
        result = fight_sans(player, small_font)
        try:
            pygame.mixer.music.load("assets/geodash_music.mp3")
            pygame.mixer.music.play(-1)
        except Exception:
            pass
        return result

    if boss_cls == "OrangeMirrorBoss":
        player.hp = 23
        result = fight_orange_mirror(player, small_font)
        try:
            pygame.mixer.music.load("assets/geodash_music.mp3")
            pygame.mixer.music.play(-1)
        except Exception:
            pass
        return result

    if boss_cls == "PapyrusBoss":
        result = fight_papyrus(player, small_font)
        try:
            pygame.mixer.music.load("assets/geodash_music.mp3")
            pygame.mixer.music.play(-1)
        except Exception:
            pass
        return result

    if boss_cls == "UndyneBoss":
        result = fight_undyne(player, small_font)
        try:
            pygame.mixer.music.load("assets/geodash_music.mp3")
            pygame.mixer.music.play(-1)
        except Exception:
            pass
        return result

    if boss_cls == "TorielBoss":
        result = fight_toriel(player, small_font)
        try:
            pygame.mixer.music.load("assets/geodash_music.mp3")
            pygame.mixer.music.play(-1)
        except Exception:
            pass
        return result

    if boss_cls == "AsrielBoss":
        result = fight_asriel(player, small_font)
        try:
            pygame.mixer.music.load("assets/geodash_music.mp3")
            pygame.mixer.music.play(-1)
        except Exception:
            pass
        return result

    pygame.mixer.music.load("assets/boss_music.mp3")
    pygame.mixer.music.play(-1)
    boss = boss_cls()
    result = fight_one_boss(player, boss, small_font)
    pygame.mixer.music.load("assets/geodash_music.mp3")
    pygame.mixer.music.play(-1)
    return result


async def main():
    # ── 시작 안내 화면 ──
    intro_clock = pygame.time.Clock()
    intro_lines = [
        (korean_font_sm, "[ 조작 안내 ]",                                     YELLOW,          0),
        (korean_font_sm, "SPACE  :  점프맵에서는 점프,",                       WHITE,           1),
        (korean_font_sm, "          보스전·전투에서는 돌진 공격",               WHITE,           1),
        (korean_font_sm, "WASD   :  보스전·전투 이동",                         WHITE,           1),
        (korean_font_sm, "",                                                   WHITE,           0),
        (korean_font_sm, "[ 비밀 코드 ]",                                      YELLOW,          0),
        (korean_font_sm, "030605  →  보스 연속전",                             (180, 220, 255), 1),
        (korean_font_sm, "2014    →  보스 선택 화면",                          (180, 220, 255), 1),
        (korean_font_sm, "",                                                   WHITE,           0),
        (korean_font_sm, "Enter 를 눌러 시작",                                 (160, 255, 160), 0),
    ]
    blink = 0
    LINE_H = 30
    while True:
        for ev in poll_events():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_RETURN:
                break
        else:
            screen.fill(BLACK)
            total_h = len(intro_lines) * LINE_H
            start_y = HEIGHT // 2 - total_h // 2
            for i, (fnt, text, col, indent) in enumerate(intro_lines):
                if not text:
                    continue
                surf = fnt.render(text, True, col)
                x = WIDTH // 2 - surf.get_width() // 2 + indent * 20
                y = start_y + i * LINE_H
                # 마지막 줄(Enter 안내)은 깜빡임
                if "Enter" in text:
                    blink += 1
                    if (blink // 20) % 2 == 0:
                        screen.blit(surf, (x, y))
                else:
                    screen.blit(surf, (x, y))
            present()
            intro_clock.tick(60)
            await asyncio.sleep(0)
            continue
        break

    player, obstacles, spawn_x, zone, next_portal_x, score = reset_game()
    particles = []
    game_over = False
    code_buffer = []
    select_mode = False   # 보스 선택 모드
    select_idx = 0        # 선택 커서 인덱스

    while True:
        for event in poll_events():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # ── 보스 선택 모드 중 입력 처리 ──
            if select_mode:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        select_mode = False
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        select_idx = (select_idx - 1) % len(BOSS_SELECT_LIST)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        select_idx = (select_idx + 1) % len(BOSS_SELECT_LIST)
                    elif event.key == pygame.K_RETURN:
                        chosen_name = BOSS_SELECT_LIST[select_idx]
                        boss_cls = BOSS_NAME_MAP.get(chosen_name)
                        if boss_cls:
                            select_mode = False
                            run_single_boss(boss_cls)
                continue  # 선택 모드 중 나머지 이벤트 무시

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and game_over:
                    player, obstacles, spawn_x, zone, next_portal_x, score = reset_game()
                    particles = []
                    game_over = False

                # 코드 버퍼 갱신 (두 치트코드 모두 감지)
                code_buffer.append(event.key)
                code_buffer = code_buffer[-_MAX_CODE_LEN:]
                if code_buffer[-len(BOSS_CODE):] == BOSS_CODE:
                    run_boss_fight()
                    code_buffer = []
                elif code_buffer[-len(BOSS_SELECT_CODE):] == BOSS_SELECT_CODE:
                    select_mode = True
                    select_idx = 0
                    code_buffer = []

        if not game_over:
            spawn_x -= SCROLL_SPEED
            keys = pygame.key.get_pressed()

            if player.mode == "cube":
                player.on_ground = False
                player.apply_gravity()
            else:
                player.fly(keys[pygame.K_SPACE])
                player.y = max(0, player.y)

            for obs in obstacles:
                obs.update()

            # 화면 밖으로 나간 장애물은 제거하고 지나간 만큼 점수 증가
            while obstacles and obstacles[0].right < 0:
                obstacles.pop(0)
                score += 1

            # 새 패턴이 필요하면 화면 오른쪽 밖에 미리 생성 (포탈 지점이면 포탈을 먼저 생성)
            if spawn_x < WIDTH + 250:
                if spawn_x >= next_portal_x:
                    new_zone = "ship" if zone == "cube" else "cube"
                    obstacles.append(Portal(spawn_x, new_zone))
                    zone = new_zone
                    spawn_x += 80
                    next_portal_x = spawn_x + random.randint(500, 800)
                else:
                    new_obs, spawn_x = make_pattern(spawn_x, zone)
                    obstacles.extend(new_obs)

            # 포탈 통과 체크: 닿으면 무조건(강제로) 모드가 바뀜. 죽지는 않음.
            # 착지 상태에서 비행 모드로 들어가면 같은 프레임에 바닥 충돌로 즉사하지 않도록 살짝 띄워준다.
            for obs in obstacles:
                if isinstance(obs, Portal) and not obs.triggered and obs.x <= player.x + player.size:
                    player.mode = obs.to_mode
                    if obs.to_mode == "ship":
                        player.y -= 15
                        player.vel_y = -2
                    else:
                        player.vel_y = 0
                    obs.triggered = True

            new_bottom = player.y + player.size
            over_pit = any(
                isinstance(obs, Pit) and obs.contains_x(player.x) or
                isinstance(obs, Pit) and obs.contains_x(player.x + player.size)
                for obs in obstacles
            )

            # 바닥 충돌 (낭떠러지 위에서는 바닥이 없다)
            landed = False
            if over_pit:
                if player.y > HEIGHT:
                    game_over = True
            elif player.mode == "cube" and new_bottom >= GROUND_Y:
                player.land_on(GROUND_Y)
                landed = True
            elif player.mode == "ship" and new_bottom >= GROUND_Y:
                game_over = True
            elif player.mode == "ship" and player.y <= 0:
                game_over = True

            # 장애물 충돌
            for obs in obstacles:
                if isinstance(obs, (Portal, Pit)):
                    continue
                if isinstance(obs, Pillar):
                    overlap_x = player.x < obs.right and player.x + player.size > obs.x
                    if not overlap_x:
                        continue
                    if (not landed and player.vel_y >= 0
                            and player.prev_bottom <= obs.y and new_bottom >= obs.y):
                        player.land_on(obs.y)
                        landed = True
                    elif player.get_rect().colliderect(obs.get_rect()):
                        game_over = True
                else:
                    if player.get_rect().colliderect(obs.get_rect()):
                        game_over = True

            # 스페이스바를 누르고 있으면 착지하자마자 딜레이 없이 바로 다시 점프 (연속 점프)
            if player.mode == "cube" and keys[pygame.K_SPACE] and player.on_ground:
                player.jump()

            # 이동 파티클: 플레이어 뒤쪽에서 생성
            particles.append(Particle(player.x, player.y + player.size - 2))
            for p in particles:
                p.update()
            particles = [p for p in particles if p.alive()]

        # 그리기
        screen.fill(BLACK)
        pygame.draw.line(screen, WHITE, (0, GROUND_Y), (WIDTH, GROUND_Y), 2)

        for p in particles:
            p.draw()

        player.draw()
        for obs in obstacles:
            obs.draw()

        score_text = font.render(str(score), True, WHITE)
        screen.blit(score_text, (20, 20))

        mode_text = font.render(player.mode.upper(), True, YELLOW if player.mode == "ship" else CYAN)
        screen.blit(mode_text, (WIDTH - mode_text.get_width() - 20, 20))

        if game_over:
            over_text = font.render("Game Over - SPACE to restart", True, WHITE)
            screen.blit(over_text, (WIDTH // 2 - over_text.get_width() // 2, HEIGHT // 2 - 20))

        if select_mode:
            # 반투명 배경
            _ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            _ov.fill((0, 0, 0, 185))
            screen.blit(_ov, (0, 0))

            # 패널 (보스 목록이 늘어나도 화면 높이 안에 들어오도록 줄 높이를 계산)
            _header_h, _footer_h = 44, 28
            _row_h = min(52, max(24, (HEIGHT - 16 - _header_h - _footer_h) // len(BOSS_SELECT_LIST)))
            _pw = 420
            _ph = _header_h + len(BOSS_SELECT_LIST) * _row_h + _footer_h
            _px = WIDTH // 2 - _pw // 2
            _py = max(8, HEIGHT // 2 - _ph // 2)
            pygame.draw.rect(screen, (20, 20, 40), (_px, _py, _pw, _ph), border_radius=12)
            pygame.draw.rect(screen, (100, 100, 200), (_px, _py, _pw, _ph), 2, border_radius=12)

            _title = korean_font_sm.render("★  보스 선택  ★", True, YELLOW)
            screen.blit(_title, (WIDTH // 2 - _title.get_width() // 2, _py + 10))

            _BOSS_COLORS = [
                (255, 140,  60),   # 드래곤
                (140, 200, 255),   # 기사
                (180,  80, 255),   # 마왕
                (255, 165,  60),   # 거울속의 나
                (100, 220, 255),   # 샌즈
                (255, 120,  40),   # 파피루스
                ( 80, 210, 120),   # 언다인
                (255, 160,  60),   # 토리엘
                (220, 170, 255),   # 아스리엘
            ]
            _row_pad = (_row_h - 26) // 2
            for _i, _bname in enumerate(BOSS_SELECT_LIST):
                _iy = _py + _header_h + _i * _row_h
                _selected = (_i == select_idx)
                if _selected:
                    _sel_rect = pygame.Rect(_px + 12, _iy - 2, _pw - 24, _row_h - 4)
                    pygame.draw.rect(screen, (40, 40, 90), _sel_rect, border_radius=8)
                    pygame.draw.rect(screen, _BOSS_COLORS[_i], _sel_rect, 2, border_radius=8)
                    _arrow = korean_font_sm.render("▶", True, _BOSS_COLORS[_i])
                    screen.blit(_arrow, (_px + 20, _iy + _row_pad))
                _col = _BOSS_COLORS[_i] if _selected else (200, 200, 200)
                _bt = korean_font_sm.render(_bname, True, _col)
                screen.blit(_bt, (WIDTH // 2 - _bt.get_width() // 2, _iy + _row_pad))

            _hint = korean_font_sm.render("↑↓ 이동    Enter 선택    ESC 취소", True, (130, 130, 150))
            screen.blit(_hint, (WIDTH // 2 - _hint.get_width() // 2, _py + _ph - _footer_h + 4))

        present()
        clock.tick(FPS)
        await asyncio.sleep(0)


if __name__ == "__main__":
    asyncio.run(main())
