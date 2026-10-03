import pyglet
from pyglet.window import key
from enum import Enum
import os

print("Script started")

# ── paths ──────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
def asset(rel):
    return os.path.join(SCRIPT_DIR, rel)

# ── game states ────────────────────────────────────────────────────────────
class GameState(Enum):
    CHAR_SELECT = 0
    PLAYING     = 1
    GAME_OVER   = 2

# ── constants ──────────────────────────────────────────────────────────────
WINDOW_WIDTH  = 800
WINDOW_HEIGHT = 600
GRAVITY       = -1500
COLLISION_DAMAGE           = 5
FIGHTER_WIDTH              = 50
FIGHTER_HEIGHT             = 100
BOUNCE_VELOCITY            = 300
PUSH_VELOCITY              = -200
HORIZONTAL_FORCE           = 150
VERTICAL_DAMAGE_MULTIPLIER = 1.5

# ── character definitions ──────────────────────────────────────────────────
CHARACTERS = [
    {'name': 'Shadow',  'image': 'blue_ninja.png',         'speed': 300, 'power': 1.0, 'health': 100, 'scale': 0.5},
    {'name': 'Blaze',   'image': 'purple_ninja.png',       'speed': 260, 'power': 1.4, 'health': 90,  'scale': 0.5},
    {'name': 'Frost',   'image': 'blue_ninja.png',         'speed': 350, 'power': 0.8, 'health': 110, 'scale': 0.45},
    {'name': 'Venom',   'image': 'purple_ninja.png',       'speed': 240, 'power': 1.6, 'health': 85,  'scale': 0.55},
    {'name': 'Storm',   'image': 'blue_ninja.png',         'speed': 400, 'power': 0.7, 'health': 120, 'scale': 0.42},
]

# ── stage definitions ──────────────────────────────────────────────────────
STAGES = [
    {'name': 'Dojo',    'bg': 'background.png'},
    {'name': 'Forest',  'bg': 'background.png'},   # reuse until more bgs exist
    {'name': 'Volcano', 'bg': 'background.png'},
]
STAGE_TINTS = [
    (255, 255, 255),   # Dojo   – no tint
    (180, 230, 180),   # Forest – green tint
    (255, 190, 140),   # Volcano – orange tint
]

# ── window ─────────────────────────────────────────────────────────────────
print("Creating window")
window = pyglet.window.Window(width=WINDOW_WIDTH, height=WINDOW_HEIGHT,
                              caption="NinjaClash2D")
print("Window created")

batch = pyglet.graphics.Batch()

# ── load assets ────────────────────────────────────────────────────────────
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
for name in ['background.png', 'blue_ninja.png', 'purple_ninja.png']:
    img = load_image(name)
    if img:
        images[name] = img
        print(f"Loaded {name}")

try:
    jump_sound = pyglet.media.load(asset('jump.wav'),   streaming=False)
    hit_sound  = pyglet.media.load(asset('hit.wav'),    streaming=False)
    print("Loaded sounds")
except Exception as e:
    print(f"Sound load failed: {e}")
    _sil = pyglet.media.StaticSource(pyglet.media.Silence(1))
    jump_sound = hit_sound = _sil

# ── Fighter ────────────────────────────────────────────────────────────────
class Fighter(pyglet.sprite.Sprite):
    def __init__(self, x, y, image, batch, controls, char_data, face_right=True):
        super().__init__(image, x=x, y=y, batch=batch)
        self.char_data   = char_data
        self.velocity_x  = 0
        self.velocity_y  = 0
        self.on_ground   = False
        self.health      = char_data['health']
        self.max_health  = char_data['health']
        self.controls    = controls
        self.face_right  = face_right
        self.scale       = char_data['scale']
        self._spd        = char_data['speed']
        self._pow        = char_data['power']
        if not face_right:
            self.scale_x *= -1
        self.collision_cooldown = 0
        self.attacking          = False
        self.attack_cooldown    = 0
        self.attack_type        = None
        self.attack_duration    = 0
        self.original_rotation  = self.rotation
        # hit-reaction flash
        self.flash_timer = 0.0
        self.attack_states = {
            'punch': {'rotation': 20,  'duration': 0.3, 'damage': 10 * self._pow, 'range': 70,  'forward_move': 50},
            'kick':  {'rotation': -15, 'duration': 0.4, 'damage': 15 * self._pow, 'range': 80,  'forward_move': -30},
        }

    # ── movement ──
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
            self.on_ground  = False
            jump_sound.play()

    # ── attacks ──
    def punch(self):
        if not self.attacking and self.attack_cooldown <= 0:
            self.attacking       = True
            self.attack_type     = 'punch'
            self.attack_duration = self.attack_states['punch']['duration']
            self.attack_cooldown = 0.5
            rot = self.attack_states['punch']['rotation']
            self.rotation = rot if self.face_right else -rot

    def kick(self):
        if not self.attacking and self.attack_cooldown <= 0:
            self.attacking       = True
            self.attack_type     = 'kick'
            self.attack_duration = self.attack_states['kick']['duration']
            self.attack_cooldown = 0.7
            rot = self.attack_states['kick']['rotation']
            self.rotation = rot if self.face_right else -rot

    def check_attack_hit(self, other):
        if not self.attacking or not self.attack_type:
            return False
        rng = self.attack_states[self.attack_type]['range']
        if abs(self.x - other.x) <= rng:
            if self.face_right and self.x < other.x:   return True
            if not self.face_right and self.x > other.x: return True
        return False

    def take_damage(self, amount):
        if self.collision_cooldown <= 0:
            self.health = max(0, self.health - amount)
            hit_sound.play()
            self.collision_cooldown = 0.5
            self.flash_timer = 0.3          # flash white on hit

    def check_collision(self, other, new_x, new_y):
        sl = new_x - self.width/2;   sr = new_x + self.width/2
        sb = new_y;                   st = new_y + self.height
        ol = other.x - other.width/2; or_ = other.x + other.width/2
        ob = other.y;                  ot = other.y + other.height

        if sl < or_ and sr > ol and sb < ot and st > ob:
            ox = min(sr, or_) - max(sl, ol)
            oy = min(st, ot)  - max(sb, ob)
            if ox < oy:
                d = 1 if self.x < other.x else -1
                self.velocity_x  = -HORIZONTAL_FORCE * d
                other.velocity_x =  HORIZONTAL_FORCE * d
                new_x = (ol - self.width/2) if self.x < other.x else (or_ + self.width/2)
                if self.collision_cooldown <= 0:
                    other.take_damage(COLLISION_DAMAGE)
                    self.collision_cooldown = 1.0
            else:
                if sb < ob:
                    new_y = ot
                    self.velocity_y  = BOUNCE_VELOCITY
                    other.velocity_y = PUSH_VELOCITY
                    if self.collision_cooldown <= 0:
                        other.take_damage(int(COLLISION_DAMAGE * VERTICAL_DAMAGE_MULTIPLIER))
                        self.collision_cooldown = 0.5
                else:
                    new_y = ob - self.height
                    self.velocity_y = -self.velocity_y * 0.5
        return new_x, new_y

    def update(self, dt, other):
        # flash effect
        if self.flash_timer > 0:
            self.flash_timer -= dt
            self.opacity = 80 if int(self.flash_timer * 12) % 2 else 255
        else:
            self.opacity = 255

        if self.attacking:
            self.attack_duration -= dt
            d = 1 if self.face_right else -1
            fm = self.attack_states[self.attack_type]['forward_move']
            self.x += fm * d * dt * 10
            if self.attack_duration <= 0:
                self.attacking    = False
                self.rotation     = self.original_rotation
                self.attack_type  = None
            elif self.check_attack_hit(other):
                dmg = self.attack_states[self.attack_type]['damage']
                other.take_damage(dmg)

        self.velocity_y += GRAVITY * dt
        nx = self.x + self.velocity_x * dt
        ny = self.y + self.velocity_y * dt
        nx = max(self.width/2, min(nx, WINDOW_WIDTH - self.width/2))
        if ny < 0:
            ny = 0
            self.velocity_y = 0
            self.on_ground  = True
        else:
            self.on_ground = False
        nx, ny = self.check_collision(other, nx, ny)
        self.x, self.y = nx, ny
        self.velocity_x *= 0.95
        if self.collision_cooldown > 0: self.collision_cooldown -= dt
        if self.attack_cooldown    > 0: self.attack_cooldown    -= dt

# ── character select ───────────────────────────────────────────────────────
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
        # dark bg
        pyglet.shapes.Rectangle(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT,
                                 color=(20, 15, 30)).draw()
        pyglet.text.Label("SELECT YOUR FIGHTER", font_size=28, bold=True,
                          x=WINDOW_WIDTH//2, y=WINDOW_HEIGHT - 50,
                          anchor_x='center', anchor_y='center',
                          color=(255, 215, 0, 255)).draw()
        # grid
        cols, row_h, col_w = 3, 90, 120
        start_x, start_y = 80, WINDOW_HEIGHT - 130
        for i, c in enumerate(CHARACTERS):
            cx = start_x + (i % cols) * col_w
            cy = start_y - (i // cols) * row_h
            p1_sel = (i == self.p1)
            p2_sel = (i == self.p2)
            border = (100, 200, 255) if p1_sel else (255, 100, 100) if p2_sel else (60, 60, 80)
            pyglet.shapes.Rectangle(cx - 38, cy - 38, 76, 76, color=border).draw()
            pyglet.shapes.Rectangle(cx - 35, cy - 35, 70, 70, color=(30, 25, 40)).draw()
            # name
            pyglet.text.Label(c['name'], font_size=10,
                              x=cx, y=cy - 10,
                              anchor_x='center', anchor_y='center',
                              color=(255,255,255,255)).draw()
            pyglet.text.Label(f"HP:{c['health']} SP:{c['speed']//10} PW:{int(c['power']*10)}",
                              font_size=7, x=cx, y=cy - 26,
                              anchor_x='center', anchor_y='center',
                              color=(180,180,180,255)).draw()
            if self.p1_locked and p1_sel:
                pyglet.text.Label("P1✓", font_size=12, bold=True,
                                  x=cx, y=cy + 14, anchor_x='center',
                                  color=(100,200,255,255)).draw()
            if self.p2_locked and p2_sel:
                pyglet.text.Label("P2✓", font_size=12, bold=True,
                                  x=cx, y=cy + 14, anchor_x='center',
                                  color=(255,100,100,255)).draw()

        # stage row
        sy = 130
        pyglet.text.Label("STAGE:", font_size=14,
                          x=50, y=sy, anchor_x='left', anchor_y='center',
                          color=(255,215,0,255)).draw()
        for i, s in enumerate(STAGES):
            sx = 160 + i * 180
            col = (255,255,255) if i == self.stage else (80,80,80)
            pyglet.text.Label(s['name'], font_size=14,
                              x=sx, y=sy, anchor_x='center', anchor_y='center',
                              color=col+(255,)).draw()

        # instructions
        pyglet.text.Label(
            "P1: A/D select  J=lock    P2: ←/→ select  1=lock    S/↓=stage    ENTER=fight",
            font_size=10, x=WINDOW_WIDTH//2, y=28,
            anchor_x='center', anchor_y='center',
            color=(180,180,180,200)).draw()
        if self.ready:
            pyglet.text.Label("PRESS ENTER TO FIGHT!", font_size=24, bold=True,
                              x=WINDOW_WIDTH//2, y=70,
                              anchor_x='center', anchor_y='center',
                              color=(0,255,0,255)).draw()

char_select = CharSelect()

# ── helpers ────────────────────────────────────────────────────────────────
fighter1 = fighter2 = None
background_sprite = None
game_state = GameState.CHAR_SELECT

def make_fighters():
    global fighter1, fighter2, background_sprite, batch
    batch = pyglet.graphics.Batch()
    c1 = CHARACTERS[char_select.p1]
    c2 = CHARACTERS[char_select.p2]
    img1 = images.get(c1['image']) or list(images.values())[0]
    img2 = images.get(c2['image']) or list(images.values())[0]

    # background with stage tint
    bg_img = images.get('background.png')
    if bg_img:
        background_sprite = pyglet.sprite.Sprite(bg_img, x=0, y=0, batch=batch)
        background_sprite.scale_x = WINDOW_WIDTH  / background_sprite.width
        background_sprite.scale_y = WINDOW_HEIGHT / background_sprite.height
        r,g,b = STAGE_TINTS[char_select.stage]
        background_sprite.color = (r,g,b)
    else:
        r,g,b = STAGE_TINTS[char_select.stage]
        background_sprite = pyglet.shapes.Rectangle(0,0,WINDOW_WIDTH,WINDOW_HEIGHT,
                                                    color=(r,g,b), batch=batch)

    fighter1 = Fighter(150, 0, img1, batch,
                       {'left': key.LEFT, 'right': key.RIGHT,
                        'jump': key.UP, 'punch': key.SPACE, 'kick': key.RSHIFT},
                       c1, face_right=True)
    fighter2 = Fighter(650, 0, img2, batch,
                       {'left': key.A, 'right': key.D,
                        'jump': key.W, 'punch': key.LSHIFT, 'kick': key.Q},
                       c2, face_right=False)

health_bar1_bg = pyglet.shapes.Rectangle(10,  570, 200, 20, color=(60,0,0))
health_bar2_bg = pyglet.shapes.Rectangle(590, 570, 200, 20, color=(60,0,0))
health_bar1    = pyglet.shapes.Rectangle(10,  570, 200, 20, color=(0,255,0))
health_bar2    = pyglet.shapes.Rectangle(590, 570, 200, 20, color=(0,255,0))

def hbar_color(pct):
    if pct > 0.5: return (0,255,0)
    if pct > 0.25: return (255,165,0)
    return (255,0,0)

key_pressed = {}

# ── update ─────────────────────────────────────────────────────────────────
def update(dt):
    global game_state
    if game_state != GameState.PLAYING:
        return
    for f in [fighter1, fighter2]:
        c = f.controls
        if key_pressed.get(c['left']):    f.move_left()
        elif key_pressed.get(c['right']): f.move_right()
        else:                             f.stop()
        if key_pressed.get(c['jump']):    f.jump()
        if key_pressed.get(c['punch']):   f.punch()
        if key_pressed.get(c['kick']):    f.kick()

    fighter1.update(dt, fighter2)
    fighter2.update(dt, fighter1)

    for f, bar in [(fighter1, health_bar1), (fighter2, health_bar2)]:
        pct = f.health / f.max_health
        bar.width = pct * 200
        bar.color = hbar_color(pct)

    if fighter1.health <= 0 or fighter2.health <= 0:
        game_state = GameState.GAME_OVER

# ── draw ───────────────────────────────────────────────────────────────────
@window.event
def on_draw():
    window.clear()
    if game_state == GameState.CHAR_SELECT:
        char_select.draw()
        return

    batch.draw()

    # name labels
    c1n = CHARACTERS[char_select.p1]['name']
    c2n = CHARACTERS[char_select.p2]['name']
    pyglet.text.Label(c1n, font_size=12, x=15,  y=594,
                      color=(200,200,255,255)).draw()
    pyglet.text.Label(c2n, font_size=12, x=785, y=594,
                      anchor_x='right', color=(255,200,200,255)).draw()

    # health bars (drawn on top of batch)
    health_bar1_bg.draw(); health_bar1.draw()
    health_bar2_bg.draw(); health_bar2.draw()

    if game_state == GameState.GAME_OVER:
        pyglet.shapes.Rectangle(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT,
                                 color=(0,0,0)).opacity = 120  # semi-dark
        winner = CHARACTERS[char_select.p1]['name'] if fighter2.health == 0 \
                 else CHARACTERS[char_select.p2]['name']
        pyglet.text.Label(f"{winner} WINS!", font_size=48, bold=True,
                          x=WINDOW_WIDTH//2, y=WINDOW_HEIGHT//2 + 30,
                          anchor_x='center', anchor_y='center',
                          color=(255,215,0,255)).draw()
        pyglet.text.Label("ENTER = rematch    ESC = character select",
                          font_size=18, x=WINDOW_WIDTH//2, y=WINDOW_HEIGHT//2 - 40,
                          anchor_x='center', anchor_y='center',
                          color=(200,200,200,255)).draw()

# ── input ──────────────────────────────────────────────────────────────────
@window.event
def on_key_press(symbol, modifiers):
    global game_state
    key_pressed[symbol] = True

    if game_state == GameState.CHAR_SELECT:
        cs = char_select
        if not cs.p1_locked:
            if symbol == key.A:     cs.p1 = (cs.p1 - 1) % len(CHARACTERS)
            elif symbol == key.D:   cs.p1 = (cs.p1 + 1) % len(CHARACTERS)
            elif symbol == key.J:   cs.p1_locked = True
        if not cs.p2_locked:
            if symbol == key.LEFT:  cs.p2 = (cs.p2 - 1) % len(CHARACTERS)
            elif symbol == key.RIGHT: cs.p2 = (cs.p2 + 1) % len(CHARACTERS)
            elif symbol == key._1:  cs.p2_locked = True
        if symbol in (key.S, key.DOWN):
            cs.stage = (cs.stage + 1) % len(STAGES)
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
pyglet.clock.schedule_interval(update, 1/60.0)
pyglet.app.run()
print("Game loop ended")
