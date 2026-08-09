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
# 20140306 순서로 누르면 보스 선택 모드 진입
BOSS_SELECT_CODE = [pygame.K_2, pygame.K_0, pygame.K_1, pygame.K_4, pygame.K_0, pygame.K_3, pygame.K_0, pygame.K_6]
_MAX_CODE_LEN = max(len(BOSS_CODE), len(BOSS_SELECT_CODE))

pygame.init()
pygame.mixer.init()
pygame.mixer.music.load("assets/geodash_music.mp3")
pygame.mixer.music.play(-1)  # -1 = 무한 반복
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Geo Dash (Python)")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 48)
try:
    korean_font = pygame.font.Font("C:/Windows/Fonts/malgun.ttf", 34)
except Exception:
    korean_font = pygame.font.SysFont("malgungothic", 34)

DRAGON_IMAGE = pygame.image.load("assets/dragon.png").convert_alpha()
KNIGHT_IMAGE = pygame.image.load("assets/knight.png").convert_alpha()
DEMON_LORD_IMAGE = pygame.image.load("assets/demonlord.png").convert_alpha()

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
        self.parry_enabled = False  # 거울 보스전에서만 True
        self.parry_timer = 0        # >0 이면 다음 피격 방어
        self.parry_cooldown = 0     # 연속 패리 방지

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
            self.parry_timer = 20       # 약 0.33초 패리 판정 창
            self.parry_cooldown = 50    # 재사용 대기

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
        if self.bound_timer > 0:
            self.bound_timer -= 1
        if self.parry_timer > 0:
            self.parry_timer -= 1
        if self.parry_cooldown > 0:
            self.parry_cooldown -= 1
        if abs(self.knockback_vx) > 0.2 or abs(self.knockback_vy) > 0.2:
            self.x += self.knockback_vx
            self.y += self.knockback_vy
            self.knockback_vx *= 0.75
            self.knockback_vy *= 0.75
            self.x = max(self.size, min(WIDTH - self.size, self.x))
            self.y = max(self.size, min(HEIGHT - self.size, self.y))
        else:
            self.knockback_vx = 0.0
            self.knockback_vy = 0.0

    def take_damage(self, amount):
        if self.dashing or self.hit_cooldown > 0:
            return False
        # 패리 성공: 피해 없이 막음
        if self.parry_timer > 0:
            self.parry_timer = 0
            self.parry_cooldown = 50
            self.hit_cooldown = 20  # 짧은 무적으로 연속 피해 방지
            return "parried"
        self.hp -= amount
        self.hit_cooldown = 45
        return True

    def get_rect(self):
        return pygame.Rect(self.x - self.size // 2, self.y - self.size // 2, self.size, self.size)

    def draw(self):
        if self.dashing:
            color = YELLOW
        elif self.parry_timer > 0:
            color = (0, 255, 180) if self.parry_timer % 6 < 3 else CYAN
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
        self.hp = 120
        self.max_hp = 120
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
        self.pattern = random.choice(["fire_breath", "tail_swipe", "fireball_rain"])
        self.state = "telegraph"
        self.data = {}

        if self.pattern == "fire_breath":
            self.data["band_y"] = random.randint(60, HEIGHT - 60)
            self.timer = 50
        elif self.pattern == "tail_swipe":
            self.timer = 40
        else:  # fireball_rain
            points = []
            for _ in range(5):
                points.append([random.randint(40, WIDTH - 200), random.randint(40, HEIGHT - 40), 70])
            self.data["points"] = points
            self.timer = 70

    def update(self, player):
        # 근접 공격(tail_swipe) 중에는 플레이어 옆에 고정, 그 외에는 느리게 떠다님
        if not (self.pattern == "tail_swipe" and self.state in ("windup", "active")):
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
            if self.timer <= 0:
                if self.pattern == "tail_swipe":
                    # 순간이동 후 1초(60프레임) 기다렸다가 공격
                    teleport_near(self, player)
                    self.state = "windup"
                    self.timer = 60
                else:
                    self.state = "active"
                    self.timer = {"fire_breath": 30, "fireball_rain": 20}[self.pattern]

        elif self.state == "windup":
            self.timer -= 1
            if self.timer <= 0:
                self.state = "active"
                self.timer = 20

        elif self.state == "active":
            self.timer -= 1
            if self.pattern == "fire_breath":
                if abs(player.y - self.data["band_y"]) < 35:
                    if player.take_damage(1):
                        random.choice(DRAGON_SOUNDS).play()
            elif self.pattern == "tail_swipe":
                dist = math.hypot(player.x - self.x, player.y - self.y)
                if dist < 140:
                    if player.take_damage(1):
                        random.choice(DRAGON_SOUNDS).play()
            else:
                for p in self.data["points"]:
                    if p[2] <= 0:
                        dist = math.hypot(player.x - p[0], player.y - p[1])
                        if dist < 45:
                            if player.take_damage(1):
                                random.choice(DRAGON_SOUNDS).play()
            if self.timer <= 0:
                self.state = "vulnerable"
                self.timer = 90

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
            band_y = self.data["band_y"]
            band_color = RED if self.state == "active" else (120, 40, 40)
            pygame.draw.rect(screen, band_color, pygame.Rect(0, band_y - 35, WIDTH, 70))

        if self.pattern == "tail_swipe" and self.state in ("telegraph", "windup", "active"):
            ring_color = RED if self.state == "active" else (120, 40, 40)
            pygame.draw.circle(screen, ring_color, (int(self.x), int(self.y)), 140, 4)

        if self.pattern == "fireball_rain" and self.state in ("telegraph", "active"):
            for p in self.data.get("points", []):
                if p[2] <= 0:
                    pygame.draw.circle(screen, RED, (p[0], p[1]), 45)
                else:
                    pygame.draw.circle(screen, (120, 40, 40), (p[0], p[1]), 45, 3)

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
        self.hp = 140
        self.max_hp = 140
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
        self.pattern = random.choice(["shield_charge", "combo_slash", "magic_sword_energy"])
        self.state = "telegraph"
        self.data = {}

        if self.pattern == "shield_charge":
            self.timer = 35
        elif self.pattern == "combo_slash":
            self.timer = 35
        else:  # magic_sword_energy
            self.timer = 45

    def update(self, player):
        melee_pattern = self.pattern in ("shield_charge", "combo_slash")
        if not (melee_pattern and self.state in ("windup", "active")):
            wander(self, WIDTH * 0.55, WIDTH - 70)

        if self.state == "idle":
            self.timer -= 1
            if self.timer <= 0:
                self.start_pattern()

        elif self.state == "telegraph":
            self.timer -= 1
            if self.timer <= 0:
                if melee_pattern:
                    # 순간이동 후 1초(60프레임) 기다렸다가 공격
                    teleport_near(self, player)
                    self.state = "windup"
                    self.timer = 60
                else:
                    dx, dy = player.x - self.x, player.y - self.y
                    dist = math.hypot(dx, dy) or 1
                    direction = (dx / dist, dy / dist)
                    perp = (-direction[1], direction[0])
                    self.data["proj"] = {
                        "origin": (self.x, self.y), "dir": direction, "perp": perp,
                        "t": 0, "pos": (self.x, self.y),
                    }
                    self.state = "active"
                    self.timer = 70

        elif self.state == "windup":
            self.timer -= 1
            if self.timer <= 0:
                self.state = "active"
                self.timer = {"shield_charge": 25, "combo_slash": 45}[self.pattern]

        elif self.state == "active":
            self.timer -= 1
            if self.pattern == "shield_charge":
                if in_cardinal_wedge(self, player, 170):
                    if player.take_damage(1):
                        random.choice(SWORD_SOUNDS).play()
            elif self.pattern == "combo_slash":
                if in_cardinal_wedge(self, player, 190):
                    if player.take_damage(1):
                        random.choice(SWORD_SOUNDS).play()
            else:  # magic_sword_energy
                proj = self.data["proj"]
                proj["t"] += 1
                ox, oy = proj["origin"]
                dx, dy = proj["dir"]
                px, py = proj["perp"]
                speed = 4
                wave = math.sin(proj["t"] * 0.2) * 30
                x = ox + dx * speed * proj["t"] + px * wave
                y = oy + dy * speed * proj["t"] + py * wave
                proj["pos"] = (x, y)
                if math.hypot(player.x - x, player.y - y) < 26:
                    player.take_damage(1)
            if self.timer <= 0:
                self.state = "vulnerable"
                self.timer = 90

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
            color = RED if self.state == "active" else (120, 40, 40)
            for d in CARDINAL_DIRS:
                pygame.draw.polygon(screen, color, wedge_points(self.x, self.y, d, 170), 3)

        if self.pattern == "combo_slash" and self.state in ("telegraph", "windup", "active"):
            color = RED if self.state == "active" else (120, 40, 40)
            for d in CARDINAL_DIRS:
                pygame.draw.polygon(screen, color, wedge_points(self.x, self.y, d, 190), 3)

        if self.pattern == "magic_sword_energy" and self.state == "active":
            x, y = self.data["proj"]["pos"]
            pygame.draw.circle(screen, RED, (int(x), int(y)), 14)

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
        self.hp = 320
        self.max_hp = 320
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
                "dark_barrier", "black_hole", "shadow_chains", "doomsday_laser"]
        if self.enraged:
            pool.append("enrage_combo")
        self.pattern = random.choice(pool)
        self.state = "telegraph"
        self.data = {}
        self.timer = {
            "shadow_arrow": 27, "mirror_clone": 27, "hellfire": 33,
            "dark_barrier": 27, "black_hole": 23, "shadow_chains": 23,
            "doomsday_laser": 40, "enrage_combo": 27,
        }[self.pattern]
        # telegraph 중 draw가 접근하는 값은 여기서 미리 설정
        if self.pattern == "black_hole":
            self.data["cx"] = random.randint(WIDTH // 5, WIDTH // 2)
            self.data["cy"] = random.randint(HEIGHT // 5, 4 * HEIGHT // 5)
        elif self.pattern == "doomsday_laser":
            self.data["side"] = random.choice(["top", "bottom", "left", "right"])

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

            if self.timer <= 0:
                self.state = "vulnerable"
                self.timer = 40 if self.enraged else 60

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
BOSS_NAME_MAP = {"드래곤": DragonBoss, "기사": KnightBoss, "마왕": DemonLordBoss}


class OrangeMirrorBoss:
    """히든 보스: 주황색 거울. 주인공과 똑같이 생긴 주황색 사각형.
    패턴: 미러 대쉬, 점프 스탬프, 잔상 폭발, 분열 공격, (각성)오렌지 오버드라이브."""

    name = "???"

    def __init__(self):
        self.size = 26
        self.x = float(WIDTH - 120)
        self.y = float(HEIGHT // 2)
        self.hp = 80
        self.max_hp = 80
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
        pool = ["mirror_dash", "jump_stamp", "phantom_trail", "split_squares"]
        if self.enraged:
            pool.append("orange_overdrive")
        self.pattern = random.choice(pool)
        self.state = "telegraph"
        self.data = {}
        self.timer = {
            "mirror_dash": 30, "jump_stamp": 35, "phantom_trail": 25,
            "split_squares": 30, "orange_overdrive": 20,
        }[self.pattern]

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
                        if player.take_damage(2):
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
                        player.take_damage(1)
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

            if self.timer <= 0:
                self.state = "vulnerable"
                self.timer = 120  # 2초 공격 기회

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
        # 분열 상태에서는 본체를 작게 그림
        if self.pattern == "split_squares" and self.state == "active":
            s = max(8, self.size // 3)
            col = (255, 50, 0) if self.enraged else ORANGE
            pygame.draw.rect(screen, col, pygame.Rect(int(self.x) - s // 2, int(self.y) - s // 2, s, s))
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

        bar_w = 220
        pygame.draw.rect(screen, (60, 60, 60), (WIDTH // 2 - bar_w // 2, 16, bar_w, 16))
        bar_col = (255, 50, 0) if self.enraged else ORANGE
        pygame.draw.rect(screen, bar_col,
                         (WIDTH // 2 - bar_w // 2, 16,
                          int(bar_w * max(self.hp, 0) / self.max_hp), 16))
        label = self.name + (" [OVERDRIVE]" if self.enraged else "")
        name_text = small_font.render(label, True, bar_col)
        screen.blit(name_text, (WIDTH // 2 - name_text.get_width() // 2, 34))


def fight_one_boss(player, boss, small_font, particle_colors=None):
    """보스 하나와 싸운다. 'win', 'lose', 'quit' 중 하나를 반환."""
    result = None
    move_particles = []
    prev_x, prev_y = player.x, player.y

    while result is None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    result = "quit"
                if event.key == pygame.K_SPACE:
                    player.try_dash()

        keys = pygame.key.get_pressed()
        player.handle_move(keys)
        player.update()
        boss.update(player)

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

        hp_text = small_font.render(f"HP: {max(player.hp, 0)}", True, WHITE)
        screen.blit(hp_text, (20, 20))
        hint = small_font.render("이동: WASD/방향키   돌진공격: SPACE   나가기: ESC", True, WHITE)
        screen.blit(hint, (20, HEIGHT - 30))

        pygame.display.flip()
        clock.tick(FPS)

    message = {"win": f"{boss.name} DEFEATED!", "lose": "GAME OVER", "quit": ""}[result]
    if message:
        screen.fill(BLACK)
        text = font.render(message, True, WHITE)
        screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 2 - 20))
        pygame.display.flip()
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
        for event in pygame.event.get():
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
        pygame.display.flip()
        clock.tick(FPS)

    # ── 전투 ──
    player.parry_enabled = True
    _mirror_colors = [GREEN, WHITE, RED]
    move_particles = []
    prev_x, prev_y = player.x, player.y
    parry_flash = 0   # 패리 성공 시 화면 번쩍임
    result = None
    while result is None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    result = "quit"
                if event.key == pygame.K_SPACE:
                    player.try_dash()
                if event.key == pygame.K_BACKSPACE:
                    player.try_parry()

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
            flash_surf.fill((0, 255, 180, int(180 * parry_flash / 12)))
            screen.blit(flash_surf, (0, 0))

        boss.draw(small_font)
        for p in move_particles:
            ratio = p["life"] / p["max_life"]
            r, g, b = p["color"]
            pygame.draw.circle(screen, (int(r * ratio), int(g * ratio), int(b * ratio)),
                               (int(p["x"]), int(p["y"])), max(1, int(4 * ratio)))
        player.draw()

        # 패리 상태 UI
        hp_text = small_font.render(f"HP: {max(player.hp, 0)}", True, WHITE)
        screen.blit(hp_text, (20, 20))
        if player.parry_timer > 0:
            parry_text = small_font.render("★ PARRY READY ★", True, (0, 255, 180))
            screen.blit(parry_text, (WIDTH // 2 - parry_text.get_width() // 2, HEIGHT - 55))
        elif parry_flash > 0:
            parry_text = small_font.render("PARRIED!", True, (0, 255, 180))
            screen.blit(parry_text, (WIDTH // 2 - parry_text.get_width() // 2, HEIGHT - 55))

        # 취약 상태일 때 남은 공격 시간 표시
        if boss.state == "vulnerable":
            ratio = boss.timer / 120
            bar_w = 200
            pygame.draw.rect(screen, (60, 60, 60), (WIDTH // 2 - bar_w // 2, HEIGHT - 22, bar_w, 8))
            pygame.draw.rect(screen, YELLOW, (WIDTH // 2 - bar_w // 2, HEIGHT - 22, int(bar_w * ratio), 8))
            atk_text = small_font.render("ATTACK NOW!", True, YELLOW)
            screen.blit(atk_text, (WIDTH // 2 - atk_text.get_width() // 2, HEIGHT - 40))

        hint = small_font.render("이동: WASD   돌진: SPACE   방어: BACKSPACE   나가기: ESC", True, (120, 120, 120))
        screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 14))
        pygame.display.flip()
        clock.tick(FPS)

    player.parry_enabled = False

    if result == "win":
        # ── 아웃트로: 보스가 주인공 색으로 변하며 흡수 ──
        for i in range(120):
            for event in pygame.event.get():
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
            pygame.display.flip()
            clock.tick(FPS)
        screen.fill(BLACK)
        msg = font.render("TRUE VICTORY", True, ORANGE)
        screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2 - 20))
        pygame.display.flip()
        pygame.time.wait(2500)
    elif result == "lose":
        screen.fill(BLACK)
        msg = font.render("GAME OVER", True, WHITE)
        screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2 - 20))
        pygame.display.flip()
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


def run_single_boss(boss_cls):
    """보스 선택 모드에서 특정 보스 하나와 싸운다."""
    pygame.mixer.music.load("assets/boss_music.mp3")
    pygame.mixer.music.play(-1)
    player = BossPlayer()
    small_font = pygame.font.SysFont(None, 28)
    boss = boss_cls()
    result = fight_one_boss(player, boss, small_font)
    pygame.mixer.music.load("assets/geodash_music.mp3")
    pygame.mixer.music.play(-1)
    return result


async def main():
    player, obstacles, spawn_x, zone, next_portal_x, score = reset_game()
    particles = []
    game_over = False
    code_buffer = []
    select_mode = False   # 보스 선택 모드
    select_text = ""      # 입력 확정된 텍스트
    select_editing = ""   # IME 조합 중인 텍스트

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # ── 보스 선택 모드 중 입력 처리 ──
            if select_mode:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        select_mode = False
                        select_text = ""
                        select_editing = ""
                        pygame.key.stop_text_input()
                    elif event.key == pygame.K_BACKSPACE:
                        select_text = select_text[:-1]
                    elif event.key == pygame.K_RETURN:
                        boss_cls = BOSS_NAME_MAP.get(select_text.strip())
                        if boss_cls:
                            pygame.key.stop_text_input()
                            run_single_boss(boss_cls)
                        select_mode = False
                        select_text = ""
                        select_editing = ""
                        pygame.key.stop_text_input()
                elif event.type == pygame.TEXTINPUT:
                    select_text += event.text
                    select_editing = ""
                    # 이름이 완성되는 즉시 자동 진입
                    boss_cls = BOSS_NAME_MAP.get(select_text.strip())
                    if boss_cls:
                        pygame.key.stop_text_input()
                        select_mode = False
                        select_text = ""
                        run_single_boss(boss_cls)
                elif event.type == pygame.TEXTEDITING:
                    select_editing = event.text
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
                    select_text = ""
                    select_editing = ""
                    pygame.key.start_text_input()
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
            overlay = pygame.Surface((WIDTH, 90), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 200))
            screen.blit(overlay, (0, HEIGHT // 2 - 45))
            display = select_text + select_editing + "|"
            title = korean_font.render("보스 선택 (드래곤 / 기사 / 마왕)", True, YELLOW)
            typed = korean_font.render(display, True, WHITE)
            esc_hint = korean_font.render("ESC: 취소   Enter: 확인", True, (160, 160, 160))
            screen.blit(title,    (WIDTH // 2 - title.get_width() // 2,    HEIGHT // 2 - 38))
            screen.blit(typed,    (WIDTH // 2 - typed.get_width() // 2,    HEIGHT // 2 - 8))
            screen.blit(esc_hint, (WIDTH // 2 - esc_hint.get_width() // 2, HEIGHT // 2 + 22))

        pygame.display.flip()
        clock.tick(FPS)
        await asyncio.sleep(0)


if __name__ == "__main__":
    asyncio.run(main())
