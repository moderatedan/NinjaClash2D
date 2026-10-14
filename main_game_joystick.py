import pyglet
from pyglet.window import key
from enum import Enum
import os
import time

print("Script started")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
def asset(rel):
    return os.path.join(SCRIPT_DIR, rel)

class GameState(Enum):
    INTRO = 0
    CHAR_SELECT = 1
    PLAYING = 2
    GAME_OVER = 3

WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
GRAVITY = -1500
COLLISION_DAMAGE = 5
FIGHTER_WIDTH = 50
FIGHTER_HEIGHT = 100
BOUNCE_VELOCITY = 300
PUSH_VELOCITY = -200
HORIZONTAL_FORCE = 150
VERTICAL_DAMAGE_MULTIPLIER = 1.5

CHARACTERS = [
    {'name': 'Shadow', 'image': 'blue_ninja.png', 'speed': 300, 'power': 1.0, 'health': 100, 'scale': 0.5},
    {'name': 'Blaze', 'image': 'purple_ninja.png', 'speed': 260, 'power': 1.4, 'health': 90, 'scale': 0.5},
    {'name': 'Slime', 'image': 'slime_buddy.png', 'speed': 180, 'power': 0.8, 'health': 140, 'scale': 0.6},
    {'name': 'Dino', 'image': 'robo_dino.png', 'speed': 220, 'power': 1.8, 'health': 110, 'scale': 0.7},
]

STAGES = [
    {'name': 'Stadium', 'bg': 'background.png'},
    {'name': 'Waffle Haus', 'bg': 'stage_1.jpg'},
    {'name': 'WH', 'bg': 'stage_2.jpg'},
]

print("Creating window")
window = pyglet.window.Window(width=WINDOW_WIDTH, height=WINDOW_HEIGHT, caption="NinjaClash2D")
print("Window created")

batch = pyglet.graphics.Batch()

def load_image(filename):
    path = asset(filename)
    if os.path.exists(path):
        try:
            return pyglet.image.load(path)
        except Exception as e:
            print(f"Failed to load {filename}: {e}")
    else:
        print(f"Not found: {path}")
    return None

images = {}
for name in ['background.png', 'blue_ninja.png', 'purple_ninja.png',
             'slime_buddy.png', 'robo_dino.png',
             'stage_1.jpg', 'stage_2.jpg',
             'battle_arena_bg.png', 'waffles_haus_bg.png']:
    img = load_image(name)
    if img:
        images[name] = img
        print(f"Loaded {name}")

try:
    jump_sound = pyglet.media.load(asset('jump.wav'), streaming=False)
    hit_sound = pyglet.media.load(asset('hit.wav'), streaming=False)
    print("Loaded sounds")
except:
    jump_sound = hit_sound = None

class Fighter(pyglet.sprite.Sprite):
    def __init__(self, x, y, image, batch, controls, char_data, face_right=True):
        super().__init__(image, x=x, y=y, batch=batch)
        self.char_data = char_data
        self.velocity_x = 0
        self.velocity_y = 0
        self.on_ground = False
        self.health = char_data['health']
        self.max_health = char_data['health']
        self.controls = controls
        self.face_right = face_right
        self.scale = char_data['scale']
        self._spd = char_data['speed']
        self._pow = char_data['power']
        if not face_right:
            self.scale_x *= -1
        self.collision_cooldown = 0
        self.attacking = False
        self.attack_cooldown = 0
        self.attack_type = None
        self.attack_duration = 0
        self.original_rotation = self.rotation
        self.flash_timer = 0.0
        self.attack_states = {
            'punch': {'rotation': 20, 'duration': 0.3, 'damage': 10 * self._pow, 'range': 70, 'forward_move': 50},
            'kick': {'rotation': -15, 'duration': 0.4, 'damage': 15 * self._pow, 'range': 80, 'forward_move': -30},
        }

    def move_left(self):
        self.velocity_x = -self._spd
        if self.face_right:
            self.face_right = False
            self.scale_x *= -1

    def move_right(self):
        self.velocity_x = self._spd
        if not self.face_right:
            self.face_right = True
            self.scale_x *= -1

    def stop(self):
        self.velocity_x = 0

    def jump(self):
        if self.on_ground:
            self.velocity_y = 600
            self.on_ground = False
            if jump_sound:
                jump_sound.play()

    def punch(self):
        if not self.attacking and self.attack_cooldown <= 0:
            self.attacking = True
            self.attack_type = 'punch'
            self.attack_duration = self.attack_states['punch']['duration']
            self.attack_cooldown = 0.5
            rot = self.attack_states['punch']['rotation']
            self.rotation = rot if self.face_right else -rot

    def kick(self):
        if not self.attacking and self.attack_cooldown <= 0:
            self.attacking = True
            self.attack_type = 'kick'
            self.attack_duration = self.attack_states['kick']['duration']
            self.attack_cooldown = 0.7
            rot = self.attack_states['kick']['rotation']
            self.rotation = rot if self.face_right else -rot

    def check_attack_hit(self, other):
        if not self.attacking or not self.attack_type:
            return False
        rng = self.attack_states[self.attack_type]['range']
        if abs(self.x - other.x) <= rng:
            if self.face_right and self.x < other.x:
                return True
            if not self.face_right and self.x > other.x:
                return True
        return False

    def take_damage(self, amount):
        if self.collision_cooldown <= 0:
            self.health = max(0, self.health - amount)
            if hit_sound:
                hit_sound.play()
            self.collision_cooldown = 0.5
            self.flash_timer = 0.3

    def check_collision(self, other, new_x, new_y):
        sl = new_x - self.width / 2
        sr = new_x + self.width / 2
        sb = new_y
        st = new_y + self.height
        ol = other.x - other.width / 2
        or_ = other.x + other.width / 2
        ob = other.y
        ot = other.y + other.height

        if sl < or_ and sr > ol and sb < ot and st > ob:
            ox = min(sr, or_) - max(sl, ol)
            oy = min(st, ot) - max(sb, ob)
            if ox < oy:
                d = 1 if self.x < other.x else -1
                self.velocity_x = -HORIZONTAL_FORCE * d
                other.velocity_x = HORIZONTAL_FORCE * d
                new_x = (ol - self.width / 2) if self.x < other.x else (or_ + self.width / 2)
                if self.collision_cooldown <= 0:
                    other.take_damage(COLLISION_DAMAGE)
                    self.collision_cooldown = 1.0
            else:
                if sb < ob:
                    new_y = ot
                    self.velocity_y = BOUNCE_VELOCITY
                    other.velocity_y = PUSH_VELOCITY
                    if self.collision_cooldown <= 0:
                        other.take_damage(int(COLLISION_DAMAGE * VERTICAL_DAMAGE_MULTIPLIER))
                        self.collision_cooldown = 0.5
                else:
                    new_y = ob - self.height
                    self.velocity_y = -self.velocity_y * 0.5
        return new_x, new_y

    def update(self, dt, other):
        if self.flash_timer > 0:
            self.flash_timer -= dt
            self.opacity = 80 if int(self.flash_timer * 15) % 2 == 0 else 255
        else:
            self.opacity = 255

        if self.attacking:
            self.attack_duration -= dt
            d = 1 if self.face_right else -1
            fm = self.attack_states[self.attack_type]['forward_move']
            self.x += fm * d * dt * 10
            if self.attack_duration <= 0:
                self.attacking = False
                self.rotation = self.original_rotation
                self.attack_type = None
            elif self.check_attack_hit(other):
                dmg = self.attack_states[self.attack_type]['damage']
                other.take_damage(dmg)

        self.velocity_y += GRAVITY * dt
        nx = self.x + self.velocity_x * dt
        ny = self.y + self.velocity_y * dt
        nx = max(self.width / 2, min(nx, WINDOW_WIDTH - self.width / 2))
        if ny < 0:
            ny = 0
            self.velocity_y = 0
            self.on_ground = True
        else:
            self.on_ground = False
        nx, ny = self.check_collision(other, nx, ny)
        self.x, self.y = nx, ny
        self.velocity_x *= 0.95
        if self.collision_cooldown > 0:
            self.collision_cooldown -= dt
        if self.attack_cooldown > 0:
            self.attack_cooldown -= dt

def draw_intro():
    pyglet.shapes.Rectangle(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT, color=(10, 8, 20)).draw()
    for i in range(3):
        pyglet.shapes.Rectangle(20 + i * 5, 20 + i * 5,
                                WINDOW_WIDTH - 40 - i * 10,
                                WINDOW_HEIGHT - 40 - i * 10,
                                color=(255, 215, 0, 30 - i * 10)).draw()
    pyglet.text.Label("NINJA CLASH 2D", font_size=64, bold=True,
                      x=WINDOW_WIDTH // 2, y=WINDOW_HEIGHT // 2 + 50,
                      anchor_x='center', anchor_y='center',
                      color=(255, 215, 0, 255)).draw()
    pyglet.text.Label("⚔️ Battle of the Ninjas ⚔️", font_size=24,
                      x=WINDOW_WIDTH // 2, y=WINDOW_HEIGHT // 2 - 20,
                      anchor_x='center', anchor_y='center',
                      color=(200, 200, 200, 200)).draw()
    if int(time.time() * 2) % 2 == 0:
        pyglet.text.Label("PRESS ENTER TO START", font_size=20, bold=True,
                          x=WINDOW_WIDTH // 2, y=100,
                          anchor_x='center', anchor_y='center',
                          color=(255, 255, 255, 255)).draw()

class CharSelect:
    def __init__(self):
        self.p1 = 0
        self.p2 = 1
        self.stage = 0
        self.p1_locked = False
        self.p2_locked = False

    @property
    def ready(self):
        return self.p1_locked and self.p2_locked

    def draw(self):
        # Dark background for character select
        pyglet.shapes.Rectangle(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT, color=(20, 15, 30)).draw()
        
        pyglet.text.Label("SELECT YOUR FIGHTER", font_size=32, bold=True,
                          x=WINDOW_WIDTH // 2, y=WINDOW_HEIGHT - 50,
                          anchor_x='center', anchor_y='center',
                          color=(255, 215, 0, 255)).draw()

        # Player labels
        pyglet.shapes.Rectangle(40, WINDOW_HEIGHT-100, 180, 30, color=(0,50,100,100)).draw()
        pyglet.text.Label("PLAYER 1", font_size=16, bold=True,
                          x=130, y=WINDOW_HEIGHT-85,
                          anchor_x='center', anchor_y='center',
                          color=(100, 200, 255, 255)).draw()
        
        pyglet.shapes.Rectangle(WINDOW_WIDTH-220, WINDOW_HEIGHT-100, 180, 30, color=(100,0,50,100)).draw()
        pyglet.text.Label("PLAYER 2", font_size=16, bold=True,
                          x=WINDOW_WIDTH-130, y=WINDOW_HEIGHT-85,
                          anchor_x='center', anchor_y='center',
                          color=(255, 100, 100, 255)).draw()

        # Characters
        for i, c in enumerate(CHARACTERS):
            x = 140 + i * 180
            y = WINDOW_HEIGHT - 190

            p1_sel = (i == self.p1)
            p2_sel = (i == self.p2)

            color = (60, 50, 80) if p1_sel or p2_sel else (30, 25, 40)
            if p1_sel and self.p1_locked:
                color = (0, 100, 0)
            elif p2_sel and self.p2_locked:
                color = (100, 0, 0)

            pyglet.shapes.Rectangle(x - 70, y - 70, 140, 140, color=color).draw()

            if p1_sel:
                border_color = (100, 200, 255)
                border_width = 3
            elif p2_sel:
                border_color = (255, 100, 100)
                border_width = 3
            else:
                border_color = (60, 60, 80)
                border_width = 2
                
            for w in range(border_width):
                pyglet.shapes.Rectangle(x - 68 + w, y - 68 + w, 136 - w*2, 136 - w*2, color=border_color).draw()

            char_img = images.get(c['image'])
            if char_img:
                icon = pyglet.sprite.Sprite(char_img, x=x, y=y+5, batch=None)
                icon.scale = 0.4
                icon.draw()

            pyglet.text.Label(c['name'], font_size=14, bold=True,
                              x=x, y=y - 85,
                              anchor_x='center', anchor_y='center',
                              color=(255, 255, 255, 255)).draw()

            pyglet.shapes.Rectangle(x-40, y-100, 80, 6, color=(40,40,40)).draw()
            hp_width = int(80 * c['health'] / 140)
            hp_color = (0,255,0) if c['health'] > 100 else (255,200,0) if c['health'] > 80 else (255,100,0)
            pyglet.shapes.Rectangle(x-40, y-100, hp_width, 6, color=hp_color).draw()
            
            speed_bars = c['speed'] // 60
            for s in range(min(speed_bars, 8)):
                pyglet.shapes.Rectangle(x-40 + s*10, y-110, 6, 6, color=(100,150,255)).draw()

            if p1_sel and self.p1_locked:
                pyglet.shapes.Rectangle(x-50, y+55, 100, 20, color=(0,255,0,150)).draw()
                pyglet.text.Label("LOCKED", font_size=10, bold=True,
                                  x=x, y=y+65,
                                  anchor_x='center', anchor_y='center',
                                  color=(255, 255, 255, 255)).draw()
            if p2_sel and self.p2_locked:
                pyglet.shapes.Rectangle(x-50, y+55, 100, 20, color=(255,100,100,150)).draw()
                pyglet.text.Label("LOCKED", font_size=10, bold=True,
                                  x=x, y=y+65,
                                  anchor_x='center', anchor_y='center',
                                  color=(255, 255, 255, 255)).draw()

            if p1_sel and not self.p1_locked:
                pyglet.text.Label("◀", font_size=28,
                                  x=x-85, y=y,
                                  anchor_x='center', anchor_y='center',
                                  color=(100, 200, 255, 255)).draw()
                pyglet.text.Label("▶", font_size=28,
                                  x=x+85, y=y,
                                  anchor_x='center', anchor_y='center',
                                  color=(100, 200, 255, 255)).draw()

            if p2_sel and not self.p2_locked:
                pyglet.text.Label("◀", font_size=28,
                                  x=x-85, y=y,
                                  anchor_x='center', anchor_y='center',
                                  color=(255, 100, 100, 255)).draw()
                pyglet.text.Label("▶", font_size=28,
                                  x=x+85, y=y,
                                  anchor_x='center', anchor_y='center',
                                  color=(255, 100, 100, 255)).draw()

        # ===== STAGE SELECTOR =====
        stage_y = 120
        
        # Big bright box for stage selector
        pyglet.shapes.Rectangle(100, stage_y-45, WINDOW_WIDTH-200, 90, 
                               color=(40, 35, 50)).draw()
        pyglet.shapes.Rectangle(102, stage_y-43, WINDOW_WIDTH-204, 86, 
                               color=(60, 50, 70)).draw()
        
        pyglet.text.Label("📍 STAGE", font_size=22, bold=True,
                          x=160, y=stage_y+5,
                          anchor_x='center', anchor_y='center',
                          color=(255, 215, 0, 255)).draw()
        
        current_stage = STAGES[self.stage]['name']
        pyglet.text.Label(f"{current_stage}", font_size=32, bold=True,
                          x=WINDOW_WIDTH // 2, y=stage_y+5,
                          anchor_x='center', anchor_y='center',
                          color=(255, 255, 255, 255)).draw()
        
        pyglet.text.Label("◄", font_size=36,
                          x=WINDOW_WIDTH // 2 - 200, y=stage_y+5,
                          anchor_x='center', anchor_y='center',
                          color=(255, 215, 0, 255)).draw()
        pyglet.text.Label("►", font_size=36,
                          x=WINDOW_WIDTH // 2 + 200, y=stage_y+5,
                          anchor_x='center', anchor_y='center',
                          color=(255, 215, 0, 255)).draw()
        
        pyglet.text.Label("PRESS S OR ↓ TO CHANGE STAGE", font_size=16, bold=True,
                          x=WINDOW_WIDTH // 2, y=stage_y-30,
                          anchor_x='center', anchor_y='center',
                          color=(0, 255, 200, 255)).draw()
        
        for i, s in enumerate(STAGES):
            x = 130 + i * 110
            color = (255,215,0) if i == self.stage else (120,120,120)
            pyglet.text.Label(s['name'], font_size=12,
                              x=x, y=stage_y-55,
                              anchor_x='center', anchor_y='center',
                              color=color+(255,))
            if i == self.stage:
                pyglet.shapes.Rectangle(x-40, stage_y-60, 80, 2, 
                                       color=(255,215,0,255)).draw()

        # Controls
        pyglet.text.Label(
            "P1: A/D Select  J=Lock  |  P2: ←/→ Select  1=Lock  |  S/DOWN=Stage  |  ENTER=Fight",
            font_size=12, x=WINDOW_WIDTH // 2, y=30,
            anchor_x='center', anchor_y='center',
            color=(200, 200, 200, 200)).draw()

        if self.ready:
            for i in range(5):
                alpha = 50 + i * 40
                pyglet.shapes.Rectangle(0, 80, WINDOW_WIDTH, 50, 
                    color=(0,255,0,alpha)).draw()
            pyglet.text.Label("⚔️ BOTH READY! PRESS ENTER TO FIGHT! ⚔️",
                              font_size=24, bold=True,
                              x=WINDOW_WIDTH // 2, y=105,
                              anchor_x='center', anchor_y='center',
                              color=(0, 255, 0, 255)).draw()

char_select = CharSelect()
game_state = GameState.INTRO
fighter1 = fighter2 = None
background_sprite = None
health_bar1 = health_bar2 = None
key_pressed = {}

# ── Joystick support ─────────────────────────────────────────
import time as _time
JOY_THRESH = 0.5
_joysticks = pyglet.input.get_joysticks()
joy1 = _joysticks[0] if len(_joysticks) > 0 else None
joy2 = _joysticks[1] if len(_joysticks) > 1 else None
if joy1:
    joy1.open()
    print(f"Joystick 1: {joy1.device.name}")
if joy2:
    joy2.open()
    print(f"Joystick 2: {joy2.device.name}")

# Event-driven state dicts — updated by callbacks, read in update()
joy1_state = {'x': 0.0, 'y': 0.0, 'buttons': [False] * 12}
joy2_state = {'x': 0.0, 'y': 0.0, 'buttons': [False] * 12}

_joy_nav_cd = {}  # debounce: (player, axis, dir) -> last_time

def _nav(player, axis, value):
    if abs(value) < JOY_THRESH:
        _joy_nav_cd.pop((player, axis, 'p' if value >= 0 else 'n'), None)
        return
    direction = 'p' if value > 0 else 'n'
    k = (player, axis, direction)
    now = _time.time()
    if now - _joy_nav_cd.get(k, 0) < 0.25:
        return
    _joy_nav_cd[k] = now
    cs = char_select
    if game_state == GameState.CHAR_SELECT:
        if axis == 'x':
            delta = 1 if value > 0 else -1
            if player == 1 and not cs.p1_locked:
                cs.p1 = (cs.p1 + delta) % len(CHARACTERS)
            elif player == 2 and not cs.p2_locked:
                cs.p2 = (cs.p2 + delta) % len(CHARACTERS)
        elif axis == 'y' and value < -JOY_THRESH:
            cs.stage = (cs.stage + 1) % len(STAGES)
            print(f"Stage -> {STAGES[cs.stage]['name']}")

def _btn_press(player, button):
    global game_state
    cs = char_select
    if game_state == GameState.INTRO:
        game_state = GameState.CHAR_SELECT
    elif game_state == GameState.CHAR_SELECT:
        if player == 1:
            if button == 0 and not cs.p1_locked:
                cs.p1_locked = True
            elif button in (7, 9) and cs.ready:
                make_fighters()
                game_state = GameState.PLAYING
        elif player == 2:
            if button == 0 and not cs.p2_locked:
                cs.p2_locked = True
            elif button in (7, 9) and cs.ready:
                make_fighters()
                game_state = GameState.PLAYING
    elif game_state == GameState.GAME_OVER:
        if button in (0, 7, 9):
            make_fighters()
            game_state = GameState.PLAYING

if joy1:
    @joy1.event
    def on_joyaxis_motion(joystick, axis, value):
        if axis == 'x':
            joy1_state['x'] = value
        elif axis == 'y':
            joy1_state['y'] = value
        _nav(1, axis, value)

    @joy1.event
    def on_joybutton_press(joystick, button):
        if button < len(joy1_state['buttons']):
            joy1_state['buttons'][button] = True
        _btn_press(1, button)

    @joy1.event
    def on_joybutton_release(joystick, button):
        if button < len(joy1_state['buttons']):
            joy1_state['buttons'][button] = False

if joy2:
    @joy2.event
    def on_joyaxis_motion(joystick, axis, value):
        if axis == 'x':
            joy2_state['x'] = value
        elif axis == 'y':
            joy2_state['y'] = value
        _nav(2, axis, value)

    @joy2.event
    def on_joybutton_press(joystick, button):
        if button < len(joy2_state['buttons']):
            joy2_state['buttons'][button] = True
        _btn_press(2, button)

    @joy2.event
    def on_joybutton_release(joystick, button):
        if button < len(joy2_state['buttons']):
            joy2_state['buttons'][button] = False
# ─────────────────────────────────────────────────────────────


def make_fighters():
    global fighter1, fighter2, background_sprite, health_bar1, health_bar2, batch
    batch = pyglet.graphics.Batch()
    c1 = CHARACTERS[char_select.p1]
    c2 = CHARACTERS[char_select.p2]

    img1 = images.get(c1['image'])
    if not img1:
        try:
            img1 = pyglet.image.load(asset(c1['image']))
            images[c1['image']] = img1
        except:
            img1 = pyglet.image.SolidColorImagePattern((100, 100, 255, 255)).create_image(50, 100)

    img2 = images.get(c2['image'])
    if not img2:
        try:
            img2 = pyglet.image.load(asset(c2['image']))
            images[c2['image']] = img2
        except:
            img2 = pyglet.image.SolidColorImagePattern((200, 100, 255, 255)).create_image(50, 100)

    # Add background to batch FIRST (behind fighters)
    bg_name = STAGES[char_select.stage]['bg']
    bg_img = images.get(bg_name)
    if bg_img:
        background_sprite = pyglet.sprite.Sprite(bg_img, x=0, y=0, batch=batch)
        bg_width = background_sprite.width
        bg_height = background_sprite.height
        scale_x = WINDOW_WIDTH / bg_width
        scale_y = WINDOW_HEIGHT / bg_height
        scale = max(scale_x, scale_y)
        background_sprite.scale = scale
        background_sprite.x = (WINDOW_WIDTH - bg_width * scale) / 2
        background_sprite.y = (WINDOW_HEIGHT - bg_height * scale) / 2
        print(f"Background: {bg_name}")
    else:
        background_sprite = pyglet.shapes.Rectangle(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT,
                                                    color=(40, 30, 40), batch=batch)

    fighter1 = Fighter(150, 0, img1, batch,
                       {'left': key.LEFT, 'right': key.RIGHT,
                        'jump': key.UP, 'punch': key.SPACE, 'kick': key.RSHIFT},
                       c1, face_right=True)
    fighter2 = Fighter(650, 0, img2, batch,
                       {'left': key.A, 'right': key.D,
                        'jump': key.W, 'punch': key.LSHIFT, 'kick': key.Q},
                       c2, face_right=False)

health_bar1_bg = pyglet.shapes.Rectangle(10, 570, 200, 20, color=(60, 0, 0))
health_bar2_bg = pyglet.shapes.Rectangle(590, 570, 200, 20, color=(60, 0, 0))
health_bar1 = pyglet.shapes.Rectangle(10, 570, 200, 20, color=(0, 255, 0))
health_bar2 = pyglet.shapes.Rectangle(590, 570, 200, 20, color=(0, 255, 0))

def hbar_color(pct):
    if pct > 0.5:
        return (0, 255, 0)
    if pct > 0.25:
        return (255, 165, 0)
    return (255, 0, 0)

def update(dt):
    global game_state
    if game_state != GameState.PLAYING:
        return
    for f in [fighter1, fighter2]:
        c = f.controls
        if key_pressed.get(c['left']):
            f.move_left()
        elif key_pressed.get(c['right']):
            f.move_right()
        else:
            f.stop()
        if key_pressed.get(c['jump']):
            f.jump()
        if key_pressed.get(c['punch']):
            f.punch()
        if key_pressed.get(c['kick']):
            f.kick()

    # ── Joystick gameplay (event-driven state) ──
    if joy1 and fighter1:
        if joy1_state['x'] < -JOY_THRESH:
            fighter1.move_left()
        elif joy1_state['x'] > JOY_THRESH:
            fighter1.move_right()
        if joy1_state['y'] > JOY_THRESH:      # up = positive in pyglet
            fighter1.jump()
        elif joy1_state['y'] < -JOY_THRESH:   # try both in case inverted
            fighter1.jump()
        if joy1_state['buttons'][0]:
            fighter1.punch()
        if joy1_state['buttons'][1]:
            fighter1.kick()
    if joy2 and fighter2:
        if joy2_state['x'] < -JOY_THRESH:
            fighter2.move_left()
        elif joy2_state['x'] > JOY_THRESH:
            fighter2.move_right()
        if joy2_state['y'] > JOY_THRESH:
            fighter2.jump()
        elif joy2_state['y'] < -JOY_THRESH:
            fighter2.jump()
        if joy2_state['buttons'][0]:
            fighter2.punch()
        if joy2_state['buttons'][1]:
            fighter2.kick()
    # ────────────────────────────────────────────
    fighter1.update(dt, fighter2)
    fighter2.update(dt, fighter1)

    for f, bar in [(fighter1, health_bar1), (fighter2, health_bar2)]:
        pct = f.health / f.max_health
        bar.width = pct * 200
        bar.color = hbar_color(pct)

    if fighter1.health <= 0 or fighter2.health <= 0:
        game_state = GameState.GAME_OVER

@window.event
def on_draw():
    window.clear()

    if game_state == GameState.INTRO:
        draw_intro()
        return

    if game_state == GameState.CHAR_SELECT:
        # Only draw character select - NO background
        char_select.draw()
        return

    # Only draw game batch during PLAYING or GAME_OVER
    batch.draw()

    c1n = CHARACTERS[char_select.p1]['name']
    c2n = CHARACTERS[char_select.p2]['name']
    pyglet.text.Label(c1n, font_size=12, x=15, y=594,
                      color=(200, 200, 255, 255)).draw()
    pyglet.text.Label(c2n, font_size=12, x=785, y=594,
                      anchor_x='right', color=(255, 200, 200, 255)).draw()

    health_bar1_bg.draw()
    health_bar1.draw()
    health_bar2_bg.draw()
    health_bar2.draw()

    if game_state == GameState.GAME_OVER:
        pyglet.shapes.Rectangle(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT,
                                color=(0, 0, 0, 150)).draw()
        winner = CHARACTERS[char_select.p1]['name'] if fighter2.health == 0 \
            else CHARACTERS[char_select.p2]['name']
        pyglet.text.Label(f"{winner} WINS!", font_size=48, bold=True,
                          x=WINDOW_WIDTH // 2, y=WINDOW_HEIGHT // 2 + 30,
                          anchor_x='center', anchor_y='center',
                          color=(255, 215, 0, 255)).draw()
        pyglet.text.Label("ENTER = rematch    ESC = character select",
                          font_size=18, x=WINDOW_WIDTH // 2, y=WINDOW_HEIGHT // 2 - 40,
                          anchor_x='center', anchor_y='center',
                          color=(200, 200, 200, 255)).draw()

@window.event
def on_key_press(symbol, modifiers):
    global game_state
    key_pressed[symbol] = True

    if game_state == GameState.INTRO:
        if symbol == key.ENTER:
            game_state = GameState.CHAR_SELECT
        return

    if game_state == GameState.CHAR_SELECT:
        cs = char_select
        if not cs.p1_locked:
            if symbol == key.A:
                cs.p1 = (cs.p1 - 1) % len(CHARACTERS)
            elif symbol == key.D:
                cs.p1 = (cs.p1 + 1) % len(CHARACTERS)
            elif symbol == key.J:
                cs.p1_locked = True
        if not cs.p2_locked:
            if symbol == key.LEFT:
                cs.p2 = (cs.p2 - 1) % len(CHARACTERS)
            elif symbol == key.RIGHT:
                cs.p2 = (cs.p2 + 1) % len(CHARACTERS)
            elif symbol == key._1:
                cs.p2_locked = True
        if symbol in (key.S, key.DOWN):
            cs.stage = (cs.stage + 1) % len(STAGES)
            print(f"📍 Stage changed to: {STAGES[cs.stage]['name']}")
        if symbol == key.ENTER and cs.ready:
            make_fighters()
            game_state = GameState.PLAYING
        return

    if game_state == GameState.GAME_OVER:
        if symbol == key.ENTER:
            make_fighters()
            game_state = GameState.PLAYING
        elif symbol == key.ESCAPE:
            char_select.p1_locked = False
            char_select.p2_locked = False
            game_state = GameState.CHAR_SELECT

@window.event
def on_key_release(symbol, modifiers):
    key_pressed[symbol] = False

print("Starting game loop")
pyglet.clock.schedule_interval(update, 1 / 60.0)
pyglet.app.run()
print("Game loop ended")
