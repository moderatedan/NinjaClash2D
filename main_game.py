import pyglet
import random
import math
from pyglet.window import key
from enum import Enum
import os
import time as _time

print("Script started")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
def asset(rel):
    return os.path.join(SCRIPT_DIR, rel)

# ── Game states ──────────────────────────────────────────────────
class GameState(Enum):
    INTRO = 0
    MODE_SELECT = 1       # NEW: 1P or 2P
    CHAR_SELECT = 2
    DIFFICULTY_SELECT = 3 # NEW: Easy / Medium / Hard
    BOSS_INTRO = 4        # NEW: "WARNING" countdown before a boss
    PLAYING = 5
    PINATA = 6            # NEW: Horse piñata bonus stage
    GAME_OVER = 7

class GameMode(Enum):
    TWO_PLAYER = 0
    ARCADE = 1            # 1-player arcade ladder

# ── Constants ────────────────────────────────────────────────────
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

# Playable roster
CHARACTERS = [
    {'name': 'Shadow', 'image': 'blue_ninja_right.png',   'speed': 300, 'power': 1.0, 'health': 100, 'scale': 0.5,
     'punch_image': 'blue_ninja_right_punch.png', 'kick_image': 'blue_ninja_right_kick.png'},
    {'name': 'Blaze',  'image': 'purple_ninja_right.png', 'speed': 260, 'power': 1.4, 'health': 90,  'scale': 0.5,
     'punch_image': 'purple_ninja_right_punch.png', 'kick_image': 'purple_ninja_right_kick.png'},
    {'name': 'Slime',  'image': 'slime_buddy.png',        'speed': 180, 'power': 0.8, 'health': 140, 'scale': 0.4,
     'jump_attack': True},
    {'name': 'Dino',   'image': 'robo_dino.png',          'speed': 220, 'power': 1.8, 'health': 110, 'scale': 0.6},
]

# Boss-only characters (not selectable by players)
BOSSES = [
    {'name': 'REX',         'image': 'robo_dino.png',   'speed': 240, 'power': 2.6, 'health': 220, 'scale': 0.8,  'boss': True,
     'tint': (255, 60, 60)},
    {'name': 'BLOOD SLIME', 'image': 'slime_buddy.png', 'speed': 210, 'power': 2.2, 'health': 200, 'scale': 0.45, 'boss': True,
     'tint': (255, 60, 60), 'jump_attack': True},
]

STAGES = [
    {'name': 'Waffles Haus', 'bg': 'waffle_new.jpg'},
    {'name': 'Battle Arena', 'bg': 'background.png'},
    {'name': 'Capitol Clash','bg': 'stage_2.jpg'},
    {'name': 'White House',  'bg': 'preview_4_stage.png'},
]

# ── Arcade ladder sequence builder ───────────────────────────────
def make_arcade_sequence(player_char_idx):
    """Returns a list of char_dicts and 'pinata' markers for arcade mode."""
    opponents = [i for i in range(len(CHARACTERS)) if i != player_char_idx]
    random.shuffle(opponents)
    seq = []
    for i, opp in enumerate(opponents):
        seq.append(CHARACTERS[opp])
        if i == 1:                # piñata bonus after 2nd fight
            seq.append('pinata')
    seq.append(BOSSES[0])         # T-Rex
    seq.append(BOSSES[1])         # Blood Slime
    return seq

# ── Window & batch ───────────────────────────────────────────────
print("Creating window")
window = pyglet.window.Window(width=WINDOW_WIDTH, height=WINDOW_HEIGHT, caption="NinjaClash2D")
print("Window created")
batch = pyglet.graphics.Batch()

# ── Image loading ────────────────────────────────────────────────
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
for name in [
    'background.png',
    'blue_ninja.png', 'purple_ninja.png',
    'blue_ninja_right.png', 'blue_ninja_left.png',
    'blue_ninja_right_punch.png', 'blue_ninja_right_kick.png',
    'blue_ninja_right_punch_1.png', 'blue_ninja_right_punch_2.png',
    'blue_ninja_right_kick_1.png',  'blue_ninja_right_kick_2.png',
    'blue_ninja_left_punch.png', 'blue_ninja_left_kick.png',
    'purple_ninja_right.png', 'purple_ninja_left.png',
    'purple_ninja_right_punch.png', 'purple_ninja_right_kick.png',
    'purple_ninja_right_punch_1.png', 'purple_ninja_right_punch_2.png',
    'purple_ninja_right_kick_1.png',  'purple_ninja_right_kick_2.png',
    'slime_buddy.png', 'robo_dino.png',
    'background.png', 'waffle_new.jpg', 'stage_1.jpg', 'stage_2.jpg', 'preview_4_stage.png',
    'battle_arena_bg.png', 'waffles_haus_bg.png', 'capitol_clash_bg.png',
]:
    img = load_image(name)
    if img:
        images[name] = img
        print(f"Loaded {name}")

# ── Sound loading ────────────────────────────────────────────────
try:
    jump_sound   = pyglet.media.load(asset('jump.wav'),   streaming=False)
    hit_sound    = pyglet.media.load(asset('hit.wav'),    streaming=False)
    attack_sound = pyglet.media.load(asset('attack.wav'), streaming=False)
    print("Loaded sounds")
except Exception as e:
    print(f"Sound load failed: {e}")
    jump_sound = hit_sound = attack_sound = None

# ── Music loading ─────────────────────────────────────────────────
# Drop a music.ogg (or music.wav / battle.ogg / battle.wav) in the game
# folder and it will loop automatically during gameplay.
music_player = None
for _mf in ['music.ogg', 'music.wav', 'battle.ogg', 'battle.wav']:
    if os.path.exists(asset(_mf)):
        try:
            _src = pyglet.media.load(asset(_mf))
            music_player = pyglet.media.Player()
            music_player.loop = True
            music_player.queue(_src)
            print(f"Loaded music: {_mf}")
            break
        except Exception as e:
            print(f"Music load failed ({_mf}): {e}")

def play_music():
    if music_player and not music_player.playing:
        music_player.play()

def stop_music():
    if music_player and music_player.playing:
        music_player.pause()


# ══════════════════════════════════════════════════════════════════
#  AI  (1-player arcade opponent)
# ══════════════════════════════════════════════════════════════════
class AI:
    """MK/SF-style zoning AI — holds mid-range, attacks from there, backs off when too close."""
    LABELS = ['EASY', 'MEDIUM', 'HARD']

    # Zones (pixels between centers)
    _ZONE_ATTACK = 110   # close enough to hit
    _ZONE_MID    = 200   # preferred "footsie" zone
    _ZONE_FAR    = 320   # start walking in from here

    # Per-difficulty tunables
    _REACT       = [0.55, 0.28, 0.10]   # re-eval interval (lower = sharper)
    _ATTACK_CHANCE = [0.30, 0.62, 0.88] # chance to attack when in range
    _ADVANCE_CHANCE= [0.45, 0.65, 0.85] # chance to step forward from mid-zone
    _JUMP_CHANCE   = [0.015, 0.04, 0.08]

    def __init__(self, difficulty=1):
        self.difficulty  = difficulty
        self._timer      = 0.0
        self._jump_cd    = 0.0
        self._idle_timer = 0.0   # how long to stay put in mid-zone

    def update(self, dt, me, target):
        self._timer     -= dt
        self._jump_cd   -= dt
        self._idle_timer -= dt

        d    = self.difficulty
        dist = abs(me.x - target.x)

        # Between evaluations: only continue a committed advance, otherwise idle
        if self._timer > 0:
            if dist > self._ZONE_FAR:
                # walk in slowly even between ticks
                if me.x < target.x: me.move_right()
                else:                me.move_left()
            else:
                me.stop()
            return

        self._timer = self._REACT[d] + random.uniform(0, 0.08)

        # ── Zone logic ────────────────────────────────────────────
        if dist > self._ZONE_FAR:
            # FAR — walk in
            if me.x < target.x: me.move_right()
            else:                me.move_left()

        elif dist > self._ZONE_MID:
            # MID-FAR — step in or hold based on difficulty
            if random.random() < self._ADVANCE_CHANCE[d]:
                if me.x < target.x: me.move_right()
                else:                me.move_left()
            else:
                me.stop()

        elif dist > self._ZONE_ATTACK:
            # SWEET SPOT — footsie zone: idle, attack, small steps
            if self._idle_timer > 0:
                me.stop()
            else:
                r = random.random()
                if r < 0.35:
                    # small step toward target
                    if me.x < target.x: me.move_right()
                    else:                me.move_left()
                elif r < 0.55:
                    # small step back
                    if me.x < target.x: me.move_left()
                    else:                me.move_right()
                else:
                    me.stop()
                    self._idle_timer = random.uniform(0.3, 0.9)

            # Attack from this zone
            if random.random() < self._ATTACK_CHANCE[d]:
                if random.random() < 0.5: me.punch()
                else:                      me.kick()

        else:
            # TOO CLOSE — back off
            if me.x < target.x: me.move_left()
            else:                me.move_right()
            # still throw an attack on the way out
            if random.random() < self._ATTACK_CHANCE[d] * 0.6:
                if random.random() < 0.5: me.punch()
                else:                      me.kick()

        # ── Jump ──────────────────────────────────────────────────
        jc = self._JUMP_CHANCE[d]
        if dist < self._ZONE_ATTACK: jc *= 2
        if me.on_ground and self._jump_cd <= 0 and random.random() < jc:
            me.jump()
            self._jump_cd = 1.2

        # ── Hard AI dodge ─────────────────────────────────────────
        if d == 2 and me.on_ground and target.attacking and dist < 120:
            if random.random() < 0.55 and self._jump_cd <= 0:
                me.jump()
                self._jump_cd = 0.7


# ══════════════════════════════════════════════════════════════════
#  Candy particle  (piñata bonus stage)
# ══════════════════════════════════════════════════════════════════
class CandyParticle:
    _COLORS = [
        (255,  50,  50), (255, 180,   0), ( 50, 230,  50),
        ( 50, 150, 255), (255, 100, 255), (255, 255,  50),
        (255, 130,   0), (160,  60, 255),
    ]

    def __init__(self, x, y):
        angle = random.uniform(0.2, math.pi - 0.2)   # upward arc
        speed = random.uniform(180, 480)
        self.x  = x + random.randint(-15, 15)
        self.y  = y + random.randint(0, 30)
        self.vx = math.cos(angle) * speed * random.choice([-1, 1])
        self.vy = math.sin(angle) * speed
        self.color  = random.choice(self._COLORS)
        self.radius = random.randint(5, 10)
        self.alive  = True

    def update(self, dt):
        self.vy += GRAVITY * 0.28 * dt
        self.x  += self.vx * dt
        self.y  += self.vy * dt
        if self.y < -30:
            self.alive = False

    def draw(self):
        if self.alive:
            pyglet.shapes.Circle(int(self.x), int(self.y), self.radius,
                                 color=self.color).draw()


# ══════════════════════════════════════════════════════════════════
#  Piñata Stage  ("Test Your Might" / car-smash equivalent)
# ══════════════════════════════════════════════════════════════════
class PinataStage:
    TIMER          = 20.0
    PINATA_HEALTH  = 50
    PX             = WINDOW_WIDTH  // 2
    PY             = 255           # horse body bottom-left y

    def __init__(self, stage_bg_name):
        self.bg_name     = stage_bg_name
        self.health      = self.PINATA_HEALTH
        self.timer       = self.TIMER
        self.candy       = []
        self.score       = 0
        self.done        = False
        self.broken      = False
        self.broken_t    = 0.0
        self.hit_flash   = 0.0
        self.sway        = 0.0    # horizontal offset in pixels
        self.sway_vel    = 0.0

    # ── hit ──────────────────────────────────────────────────────
    def hit(self, damage=1):
        if self.broken:
            return
        self.health  = max(0, self.health - damage)
        self.score  += 1
        self.hit_flash = 0.18
        self.sway_vel += 18 * (1 if random.random() < 0.5 else -1)
        self._spawn_candy(3 + self.score // 4)
        if self.health <= 0:
            self.broken = True
            self._spawn_candy(35)

    def _spawn_candy(self, count):
        for _ in range(count):
            self.candy.append(CandyParticle(self.PX + self.sway, self.PY + 35))

    # ── update ───────────────────────────────────────────────────
    def update(self, dt, fighter):
        if self.done:
            return

        # Timer & break resolution
        if not self.broken:
            self.timer -= dt
            if self.timer <= 0:
                self.timer = 0
                self.done = True
                return
        else:
            self.broken_t += dt
            if self.broken_t > 2.8:
                self.done = True
                return

        # Pendulum sway
        self.sway     += self.sway_vel * dt
        self.sway_vel -= self.sway * 6   # spring back
        self.sway_vel *= 0.88            # damping

        # Hit flash
        if self.hit_flash > 0:
            self.hit_flash -= dt

        # Candy physics
        self.candy = [c for c in self.candy if c.alive]
        for c in self.candy:
            c.update(dt)

        # Detect fighter attack hitting piñata
        if fighter and fighter.attacking and not self.broken:
            dist = abs(fighter.x - (self.PX + self.sway))
            if dist < 110:
                dmg = 2 if fighter.attack_type == 'kick' else 1
                self.hit(dmg)

    # ── draw ─────────────────────────────────────────────────────
    def draw(self):
        # Background
        bg_img = images.get(self.bg_name)
        if bg_img:
            bg = pyglet.sprite.Sprite(bg_img, x=0, y=0)
            bg.scale_x = WINDOW_WIDTH  / bg_img.width
            bg.scale_y = WINDOW_HEIGHT / bg_img.height
            bg.draw()
        else:
            pyglet.shapes.Rectangle(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT, color=(30,20,50)).draw()

        # Title bar
        pyglet.shapes.Rectangle(0, WINDOW_HEIGHT-52, WINDOW_WIDTH, 52, color=(0,0,0,190)).draw()
        pyglet.text.Label("HORSE PINATA BONUS STAGE!",
                          font_size=22, bold=True,
                          x=WINDOW_WIDTH//2, y=WINDOW_HEIGHT-26,
                          anchor_x='center', anchor_y='center',
                          color=(255, 215, 0, 255)).draw()

        # Score & timer
        pyglet.text.Label(f"HITS: {self.score}",
                          font_size=18, bold=True,
                          x=20, y=WINDOW_HEIGHT-75,
                          color=(255,220,0,255)).draw()
        if not self.broken:
            tcol = (255,50,50,255) if self.timer < 5 else (255,255,255,255)
            pyglet.text.Label(f"TIME: {self.timer:.1f}",
                              font_size=18, bold=True,
                              x=WINDOW_WIDTH//2, y=WINDOW_HEIGHT-75,
                              anchor_x='center', anchor_y='center',
                              color=tcol).draw()

        px = self.PX + int(self.sway)
        py = self.PY

        # Rope from ceiling to piñata
        rope_top = WINDOW_HEIGHT - 52
        pyglet.shapes.Line(px, rope_top, px, py + 85, width=3, color=(160,120,60)).draw()
        for i in range(5):
            ry = rope_top - i * 22
            pyglet.shapes.Circle(px, ry, 4, color=(140,100,50)).draw()

        flash = self.hit_flash > 0

        if self.broken:
            # Exploded pieces
            for i, col in enumerate([(255,80,40),(255,200,0),(100,200,255),(200,50,255)]):
                ox = math.sin(_time.time() * 3.5 + i * 1.6) * 40
                oy = math.cos(_time.time() * 2.2 + i * 1.1) * 20
                pyglet.shapes.Rectangle(px-20+int(ox), py+20+int(oy), 28, 22, color=col).draw()
            pyglet.text.Label("PINATA SMASHED! CANDY!",
                              font_size=30, bold=True,
                              x=WINDOW_WIDTH//2, y=200,
                              anchor_x='center', anchor_y='center',
                              color=(255,215,0,255)).draw()
        else:
            # ── Horse piñata body ──────────────────────────────
            hp_pct = self.health / self.PINATA_HEALTH
            stripe_cols = [(255,60,120),(255,200,0),(60,180,255),(200,60,255),(60,220,80)]
            bx, bh, bw = px - 52, 65, 105

            # Body stripes
            sw = bw // len(stripe_cols)
            for i, col in enumerate(stripe_cols):
                c = (255,255,200) if flash else col
                pyglet.shapes.Rectangle(bx + i*sw, py, sw, bh, color=c).draw()

            # Body outline
            for dx, dy, dw, dh in [
                (bx, py, bw, 2), (bx, py+bh, bw, 2),
                (bx, py, 2, bh), (bx+bw-2, py, 2, bh),
            ]:
                pyglet.shapes.Rectangle(dx, dy, dw, dh, color=(0,0,0)).draw()

            # Head (right side)
            hc = (255,255,200) if flash else (240,170,90)
            pyglet.shapes.Rectangle(bx+bw, py+20, 40, 32, color=hc).draw()
            # Nostril / snout
            pyglet.shapes.Rectangle(bx+bw+33, py+22, 8, 8, color=(200,120,60)).draw()
            # Eye
            pyglet.shapes.Circle(bx+bw+24, py+42, 5, color=(0,0,0)).draw()
            pyglet.shapes.Circle(bx+bw+25, py+43, 2, color=(255,255,255)).draw()
            # Ear
            pyglet.shapes.Rectangle(bx+bw+10, py+48, 10, 16, color=hc).draw()
            # Mane
            for m in range(5):
                mc = (255,255,200) if flash else (190,80,200)
                pyglet.shapes.Rectangle(bx+bw-6, py+bh-4-m*10, 12, 8, color=mc).draw()

            # Legs
            lc = (255,255,200) if flash else (220,140,70)
            for lx_off in [-38, -18, 18, 38]:
                pyglet.shapes.Rectangle(px+lx_off-5, py-32, 10, 32, color=lc).draw()
                pyglet.shapes.Rectangle(px+lx_off-7, py-35, 14, 5, color=(80,50,20)).draw()  # hoof

            # Tail (left side)
            tc = (255,255,200) if flash else (190,80,200)
            for t in range(4):
                pyglet.shapes.Circle(bx-5-t*4, py+bh//2+t*5, 7, color=tc).draw()

            # Damage cracks when low HP
            if hp_pct < 0.4:
                for i in range(int((0.4 - hp_pct) * 20)):
                    cx = bx + random.randint(0, bw)
                    cy = py + random.randint(0, bh)
                    pyglet.shapes.Line(cx, cy, cx+random.randint(-8,8), cy+random.randint(-8,8),
                                      width=1, color=(0,0,0,180)).draw()

            # Health bar
            pyglet.shapes.Rectangle(WINDOW_WIDTH//2-105, 48, 210, 18, color=(50,0,0)).draw()
            hpw = int(210 * hp_pct)
            hpc = (0,200,0) if hp_pct>0.5 else (255,160,0) if hp_pct>0.25 else (255,40,40)
            pyglet.shapes.Rectangle(WINDOW_WIDTH//2-105, 48, hpw, 18, color=hpc).draw()
            pyglet.text.Label("PINATA HP", font_size=11,
                              x=WINDOW_WIDTH//2, y=57,
                              anchor_x='center', anchor_y='center',
                              color=(255,255,255,200)).draw()

        # Candy particles
        for c in self.candy:
            c.draw()

        # Controls hint
        pyglet.text.Label("PUNCH [SPACE]  or  KICK [RSHIFT]  to smash!",
                          font_size=13, x=WINDOW_WIDTH//2, y=18,
                          anchor_x='center', anchor_y='center',
                          color=(200,200,200,180)).draw()


# ══════════════════════════════════════════════════════════════════
#  Fighter
# ══════════════════════════════════════════════════════════════════
class Fighter(pyglet.sprite.Sprite):
    def __init__(self, x, y, image, batch, controls, char_data, face_right=True):
        super().__init__(image, x=x, y=y, batch=batch)
        self.char_data       = char_data
        self.velocity_x      = 0
        self.velocity_y      = 0
        self.on_ground       = False
        self.health          = char_data['health']
        self.max_health      = char_data['health']
        self.controls        = controls
        self.face_right      = face_right
        self.scale           = char_data['scale']
        self._spd            = char_data['speed']
        self._pow            = char_data['power']
        if not face_right:
            self.scale_x *= -1
        # Boss tint (e.g. red for Blood Slime)
        if char_data.get('tint'):
            self.color = char_data['tint']
        self.collision_cooldown = 0
        self.hit_cooldown       = 0   # gates ALL incoming damage (separate from collision)
        self.attacking          = False
        self.attack_cooldown    = 0
        self.attack_type        = None
        self.attack_duration    = 0
        self.original_rotation  = self.rotation
        self.flash_timer        = 0.0
        self.attack_states = {
            'punch': {'rotation': 20,  'duration': 0.3, 'damage': 10 * self._pow, 'range': 70, 'forward_move':  50},
            'kick':  {'rotation': -15, 'duration': 0.4, 'damage': 15 * self._pow, 'range': 80, 'forward_move': -30},
        }
        self.idle_image  = image
        self.punch_image = images.get(char_data.get('punch_image', ''))
        self.kick_image  = images.get(char_data.get('kick_image',  ''))
        base_punch = char_data.get('punch_image', '').replace('.png', '')
        base_kick  = char_data.get('kick_image',  '').replace('.png', '')
        self.punch_frames = [images.get(f"{base_punch}_1.png"), images.get(f"{base_punch}_2.png")]
        self.kick_frames  = [images.get(f"{base_kick}_1.png"),  images.get(f"{base_kick}_2.png")]
        self.punch_frames = self.punch_frames if all(self.punch_frames) else None
        self.kick_frames  = self.kick_frames  if all(self.kick_frames)  else None
        self.anim_frame = 0
        self.anim_timer = 0.0

    # ── movement ─────────────────────────────────────────────────
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
            if jump_sound:
                jump_sound.play()

    # ── sprites ──────────────────────────────────────────────────
    def _set_attack_image(self, spr_image):
        if spr_image:
            sx = self.scale_x
            self.image  = spr_image
            self.scale_x = sx

    def _restore_idle_image(self):
        sx = self.scale_x
        self.image   = self.idle_image
        self.scale_x = sx

    # ── attacks ──────────────────────────────────────────────────
    def punch(self):
        # Slime & Blood Slime attack by jumping onto opponents
        if self.char_data.get('jump_attack'):
            self.jump()
            return
        if not self.attacking and self.attack_cooldown <= 0:
            self.attacking       = True
            self.attack_type     = 'punch'
            self.attack_duration = self.attack_states['punch']['duration']
            self.attack_cooldown = 0.5
            self.anim_frame = 0;  self.anim_timer = 0.0
            if   self.punch_frames: self._set_attack_image(self.punch_frames[0])
            elif self.punch_image:  self._set_attack_image(self.punch_image)
            else:
                rot = self.attack_states['punch']['rotation']
                self.rotation = rot if self.face_right else -rot

    def kick(self):
        # Slime & Blood Slime attack by jumping onto opponents
        if self.char_data.get('jump_attack'):
            self.jump()
            return
        if not self.attacking and self.attack_cooldown <= 0:
            self.attacking       = True
            self.attack_type     = 'kick'
            self.attack_duration = self.attack_states['kick']['duration']
            self.attack_cooldown = 0.7
            self.anim_frame = 0;  self.anim_timer = 0.0
            if   self.kick_frames: self._set_attack_image(self.kick_frames[0])
            elif self.kick_image:  self._set_attack_image(self.kick_image)
            else:
                rot = self.attack_states['kick']['rotation']
                self.rotation = rot if self.face_right else -rot

    def check_attack_hit(self, other):
        if not self.attacking or not self.attack_type:
            return False
        rng = self.attack_states[self.attack_type]['range']
        # When scale_x is negative (flipped), self.x is the RIGHT edge of the
        # sprite.  Compute the visual centre correctly for both directions.
        scx = self.x  + FIGHTER_WIDTH / 2 if self.face_right  else self.x  - FIGHTER_WIDTH / 2
        ocx = other.x + FIGHTER_WIDTH / 2 if other.face_right else other.x - FIGHTER_WIDTH / 2
        if abs(scx - ocx) <= rng:
            if self.face_right and scx < ocx:  return True
            if not self.face_right and scx > ocx: return True
        return False

    def take_damage(self, amount):
        if self.hit_cooldown <= 0:
            self.health      = max(0, self.health - amount)
            self.hit_cooldown = 0.4
            self.flash_timer  = 0.3
            if hit_sound:
                hit_sound.play()

    def check_collision(self, other, new_x, new_y):
        # new_x is always the true left edge (we update self.x directly as left
        # edge in update()).  For other, self.x is the right edge when flipped.
        sl = new_x;                    sr = new_x + FIGHTER_WIDTH
        sb = new_y;                    st = new_y + FIGHTER_HEIGHT
        ol = other.x if other.face_right else other.x - FIGHTER_WIDTH
        or_ = ol + FIGHTER_WIDTH
        ob = other.y;                  ot  = other.y + FIGHTER_HEIGHT
        if sl < or_ and sr > ol and sb < ot and st > ob:
            ox = min(sr, or_) - max(sl, ol)
            oy = min(st, ot)  - max(sb, ob)
            if ox < oy:
                d = 1 if self.x < other.x else -1
                self.velocity_x  = -HORIZONTAL_FORCE * d
                other.velocity_x =  HORIZONTAL_FORCE * d
                new_x = ol - FIGHTER_WIDTH if self.x < other.x else or_
                if self.collision_cooldown <= 0:
                    other.take_damage(COLLISION_DAMAGE)
                    self.collision_cooldown = 0.8
            else:
                if sb < ob:
                    new_y = ot
                    self.velocity_y  =  BOUNCE_VELOCITY
                    other.velocity_y =  PUSH_VELOCITY
                    if self.collision_cooldown <= 0:
                        other.take_damage(int(COLLISION_DAMAGE * VERTICAL_DAMAGE_MULTIPLIER))
                        self.collision_cooldown = 0.5
                else:
                    new_y = ob - self.height
                    self.velocity_y = -self.velocity_y * 0.5
        return new_x, new_y

    def update(self, dt, other=None):
        # Flash feedback
        if self.flash_timer > 0:
            self.flash_timer -= dt
            self.opacity = 80 if int(self.flash_timer * 15) % 2 == 0 else 255
        else:
            self.opacity = 255

        # Attack animation & hit detection
        if self.attacking:
            self.attack_duration -= dt
            self.anim_timer      += dt
            d  = 1 if self.face_right else -1
            fm = self.attack_states[self.attack_type]['forward_move']
            self.x += fm * d * dt * 10
            frames = self.punch_frames if self.attack_type == 'punch' else self.kick_frames
            if frames and self.anim_frame == 0:
                half = self.attack_states[self.attack_type]['duration'] / 2
                if self.anim_timer >= half:
                    self.anim_frame = 1
                    self._set_attack_image(frames[1])
            if self.attack_duration <= 0:
                self.attacking   = False
                self.rotation    = self.original_rotation
                self._restore_idle_image()
                self.attack_type = None
                self.anim_frame  = 0
                self.anim_timer  = 0.0
            elif other and self.check_attack_hit(other):
                other.take_damage(self.attack_states[self.attack_type]['damage'])

        # Physics
        self.velocity_y += GRAVITY * dt
        nx = self.x + self.velocity_x * dt
        ny = self.y + self.velocity_y * dt
        nx = max(0, min(nx, WINDOW_WIDTH - FIGHTER_WIDTH))
        if ny < 0:
            ny = 0;  self.velocity_y = 0;  self.on_ground = True
        else:
            self.on_ground = False
        if other:
            nx, ny = self.check_collision(other, nx, ny)
        self.x, self.y = nx, ny
        self.velocity_x *= 0.95

        # Auto-face opponent when not moving horizontally
        if other and abs(self.velocity_x) < 10:
            should_face_right = other.x > self.x
            if should_face_right != self.face_right:
                self.face_right = should_face_right
                self.scale_x *= -1

        if self.collision_cooldown > 0: self.collision_cooldown -= dt
        if self.attack_cooldown    > 0: self.attack_cooldown    -= dt
        if self.hit_cooldown       > 0: self.hit_cooldown       -= dt


# ══════════════════════════════════════════════════════════════════
#  Screen-draw helpers
# ══════════════════════════════════════════════════════════════════
def draw_intro():
    pyglet.shapes.Rectangle(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT, color=(10,8,20)).draw()
    for i in range(3):
        pyglet.shapes.Rectangle(20+i*5, 20+i*5,
                                WINDOW_WIDTH-40-i*10, WINDOW_HEIGHT-40-i*10,
                                color=(255,215,0, 30-i*10)).draw()
    pyglet.text.Label("NINJA CLASH 2D", font_size=64, bold=True,
                      x=WINDOW_WIDTH//2, y=WINDOW_HEIGHT//2+50,
                      anchor_x='center', anchor_y='center',
                      color=(255,215,0,255)).draw()
    pyglet.text.Label("Battle of the Ninjas", font_size=24,
                      x=WINDOW_WIDTH//2, y=WINDOW_HEIGHT//2-20,
                      anchor_x='center', anchor_y='center',
                      color=(200,200,200,200)).draw()
    if int(_time.time() * 2) % 2 == 0:
        pyglet.text.Label("PRESS ENTER TO START", font_size=20, bold=True,
                          x=WINDOW_WIDTH//2, y=100,
                          anchor_x='center', anchor_y='center',
                          color=(255,255,255,255)).draw()


def draw_mode_select(selected):
    pyglet.shapes.Rectangle(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT, color=(10,8,20)).draw()
    pyglet.text.Label("SELECT MODE", font_size=44, bold=True,
                      x=WINDOW_WIDTH//2, y=WINDOW_HEIGHT-90,
                      anchor_x='center', anchor_y='center',
                      color=(255,215,0,255)).draw()
    options = [
        ("1 PLAYER",  "Arcade Mode vs AI  |  Bosses  |  Pinata Bonus"),
        ("2 PLAYERS", "Local Multiplayer"),
    ]
    for i, (title, sub) in enumerate(options):
        y   = 330 - i * 150
        sel = (selected == i)
        pyglet.shapes.Rectangle(WINDOW_WIDTH//2-210, y-50, 420, 90,
                                color=(55,45,90) if sel else (25,20,35)).draw()
        bc = (255,215,0) if sel else (70,70,90)
        for side in [(0,-50,420,3),(0,38,420,3),(-210,-50,3,90),(207,-50,3,90)]:
            pyglet.shapes.Rectangle(WINDOW_WIDTH//2+side[0], y+side[1], side[2], side[3], color=bc).draw()
        tc = (255,215,0,255) if sel else (160,160,160,255)
        pyglet.text.Label(title, font_size=30, bold=True,
                          x=WINDOW_WIDTH//2, y=y+12,
                          anchor_x='center', anchor_y='center',
                          color=tc).draw()
        pyglet.text.Label(sub, font_size=13,
                          x=WINDOW_WIDTH//2, y=y-18,
                          anchor_x='center', anchor_y='center',
                          color=(160,160,160,210)).draw()
    pyglet.text.Label("UP/DOWN to choose   ENTER to confirm",
                      font_size=14, x=WINDOW_WIDTH//2, y=45,
                      anchor_x='center', anchor_y='center',
                      color=(160,160,160,200)).draw()


def draw_difficulty_select(selected):
    pyglet.shapes.Rectangle(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT, color=(10,8,20)).draw()
    pyglet.text.Label("SELECT DIFFICULTY", font_size=38, bold=True,
                      x=WINDOW_WIDTH//2, y=WINDOW_HEIGHT-80,
                      anchor_x='center', anchor_y='center',
                      color=(255,215,0,255)).draw()
    diffs = [
        ("EASY",   "Slow reactions, forgiving AI",     (60,200,60)),
        ("MEDIUM", "Balanced — a real fight",          (255,165,0)),
        ("HARD",   "Fast, aggressive, reads your moves",(255,50,50)),
    ]
    for i, (name, desc, col) in enumerate(diffs):
        y   = 380 - i * 120
        sel = (selected == i)
        pyglet.shapes.Rectangle(WINDOW_WIDTH//2-210, y-42, 420, 84,
                                color=(40,35,55) if sel else (18,15,25)).draw()
        if sel:
            for side in [(0,-42,420,3),(0,40,420,3),(-210,-42,3,84),(207,-42,3,84)]:
                pyglet.shapes.Rectangle(WINDOW_WIDTH//2+side[0], y+side[1], side[2], side[3], color=col).draw()
        tc = col+(255,) if sel else (130,130,130,255)
        pyglet.text.Label(name, font_size=28, bold=True,
                          x=WINDOW_WIDTH//2, y=y+10,
                          anchor_x='center', anchor_y='center',
                          color=tc).draw()
        pyglet.text.Label(desc, font_size=13,
                          x=WINDOW_WIDTH//2, y=y-16,
                          anchor_x='center', anchor_y='center',
                          color=(150,150,150,200)).draw()
    pyglet.text.Label("UP/DOWN to choose   ENTER to confirm   ESC = back",
                      font_size=13, x=WINDOW_WIDTH//2, y=38,
                      anchor_x='center', anchor_y='center',
                      color=(140,140,140,180)).draw()


def draw_boss_intro(boss_data, countdown):
    t = _time.time()
    pulse = abs(math.sin(t * 4)) * 40
    pyglet.shapes.Rectangle(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT,
                            color=(int(25+pulse//2), 0, 0)).draw()
    for i in range(4):
        a = int(12 + i * 8)
        pyglet.shapes.Rectangle(i*12, i*12,
                                WINDOW_WIDTH-i*24, WINDOW_HEIGHT-i*24,
                                color=(200,0,0,a)).draw()
    pyglet.text.Label("!  WARNING  !", font_size=40, bold=True,
                      x=WINDOW_WIDTH//2, y=WINDOW_HEIGHT//2+110,
                      anchor_x='center', anchor_y='center',
                      color=(255,50,50,255)).draw()
    pyglet.text.Label("BOSS APPROACHING", font_size=26,
                      x=WINDOW_WIDTH//2, y=WINDOW_HEIGHT//2+55,
                      anchor_x='center', anchor_y='center',
                      color=(255,180,0,255)).draw()
    bc = int(200 + pulse)
    pyglet.text.Label(boss_data['name'], font_size=58, bold=True,
                      x=WINDOW_WIDTH//2, y=WINDOW_HEIGHT//2-20,
                      anchor_x='center', anchor_y='center',
                      color=(255, bc, bc, 255)).draw()
    if countdown > 0:
        pyglet.text.Label(f"FIGHT STARTS IN  {int(countdown)+1}",
                          font_size=22, x=WINDOW_WIDTH//2, y=95,
                          anchor_x='center', anchor_y='center',
                          color=(255,255,255,220)).draw()


# ══════════════════════════════════════════════════════════════════
#  Character select screen
# ══════════════════════════════════════════════════════════════════
class CharSelect:
    def __init__(self, single_player=False):
        self.p1            = 0
        self.p2            = 1
        self.stage         = 0
        self.p1_locked     = False
        self.single_player = single_player
        # In 1P mode P2 selection is skipped (AI picks from arcade sequence)
        self.p2_locked     = single_player

    @property
    def ready(self):
        return self.p1_locked and self.p2_locked

    def draw(self):
        pyglet.shapes.Rectangle(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT, color=(20,15,30)).draw()
        title = "CHOOSE YOUR FIGHTER" if self.single_player else "SELECT YOUR FIGHTERS"
        pyglet.text.Label(title, font_size=32, bold=True,
                          x=WINDOW_WIDTH//2, y=WINDOW_HEIGHT-48,
                          anchor_x='center', anchor_y='center',
                          color=(255,215,0,255)).draw()

        # Player labels
        def _label_box(lx, lw, text, col):
            pyglet.shapes.Rectangle(lx, WINDOW_HEIGHT-102, lw, 30, color=(0,0,0,100)).draw()
            pyglet.text.Label(text, font_size=15, bold=True,
                              x=lx+lw//2, y=WINDOW_HEIGHT-87,
                              anchor_x='center', anchor_y='center',
                              color=col).draw()
        _label_box(30, 190, "PLAYER 1", (100,200,255,255))
        if self.single_player:
            _label_box(WINDOW_WIDTH-220, 190, "A.I. OPPONENT", (160,160,160,255))
        else:
            _label_box(WINDOW_WIDTH-220, 190, "PLAYER 2", (255,100,100,255))

        # Character cards
        for i, c in enumerate(CHARACTERS):
            x = 140 + i * 180
            y = WINDOW_HEIGHT - 195

            p1s = (i == self.p1)
            p2s = (not self.single_player and i == self.p2)

            box_col = (30,25,40)
            if p1s or p2s: box_col = (58,48,80)
            if p1s and self.p1_locked: box_col = (0,90,0)
            if p2s and self.p2_locked: box_col = (90,0,0)
            pyglet.shapes.Rectangle(x-70, y-70, 140, 140, color=box_col).draw()

            bc = (100,200,255) if p1s else (255,100,100) if p2s else (55,55,75)
            bw = 3 if (p1s or p2s) else 2
            for w in range(bw):
                pyglet.shapes.Rectangle(x-68+w, y-68+w, 136-w*2, 136-w*2, color=bc).draw()

            ci = images.get(c['image'])
            if ci:
                ico = pyglet.sprite.Sprite(ci, x=x, y=y+5); ico.scale=0.4; ico.draw()

            pyglet.text.Label(c['name'], font_size=14, bold=True,
                              x=x, y=y-84,
                              anchor_x='center', anchor_y='center',
                              color=(255,255,255,255)).draw()

            # HP bar
            pyglet.shapes.Rectangle(x-40, y-100, 80, 6, color=(40,40,40)).draw()
            hpw = int(80 * c['health']/140)
            hpc = (0,220,0) if c['health']>100 else (255,200,0) if c['health']>80 else (255,100,0)
            pyglet.shapes.Rectangle(x-40, y-100, hpw, 6, color=hpc).draw()
            # Speed dots
            for s in range(min(c['speed']//60, 8)):
                pyglet.shapes.Rectangle(x-40+s*10, y-110, 6, 6, color=(100,150,255)).draw()

            # Lock banners
            if p1s and self.p1_locked:
                pyglet.shapes.Rectangle(x-50, y+52, 100, 20, color=(0,200,0,160)).draw()
                pyglet.text.Label("LOCKED", font_size=10, bold=True,
                                  x=x, y=y+62, anchor_x='center', anchor_y='center',
                                  color=(255,255,255,255)).draw()
            if p2s and self.p2_locked:
                pyglet.shapes.Rectangle(x-50, y+52, 100, 20, color=(200,0,0,160)).draw()
                pyglet.text.Label("LOCKED", font_size=10, bold=True,
                                  x=x, y=y+62, anchor_x='center', anchor_y='center',
                                  color=(255,255,255,255)).draw()

            # Cursor arrows
            if p1s and not self.p1_locked:
                for sx, lbl in [(-88,"◀"),(88,"▶")]:
                    pyglet.text.Label(lbl, font_size=28, x=x+sx, y=y,
                                      anchor_x='center', anchor_y='center',
                                      color=(100,200,255,255)).draw()
            if p2s and not self.p2_locked:
                for sx, lbl in [(-88,"◀"),(88,"▶")]:
                    pyglet.text.Label(lbl, font_size=28, x=x+sx, y=y,
                                      anchor_x='center', anchor_y='center',
                                      color=(255,100,100,255)).draw()

        # Stage selector
        sy = 118
        pyglet.shapes.Rectangle(95, sy-48, WINDOW_WIDTH-190, 96, color=(38,33,48)).draw()
        pyglet.shapes.Rectangle(97, sy-46, WINDOW_WIDTH-194, 92, color=(55,48,68)).draw()
        pyglet.text.Label("STAGE", font_size=20, bold=True,
                          x=155, y=sy+5, anchor_x='center', anchor_y='center',
                          color=(255,215,0,255)).draw()
        pyglet.text.Label(STAGES[self.stage]['name'], font_size=30, bold=True,
                          x=WINDOW_WIDTH//2, y=sy+8,
                          anchor_x='center', anchor_y='center',
                          color=(255,255,255,255)).draw()
        for sx, lbl in [(-210,"◄"),(210,"►")]:
            pyglet.text.Label(lbl, font_size=34, x=WINDOW_WIDTH//2+sx, y=sy+5,
                              anchor_x='center', anchor_y='center',
                              color=(255,215,0,255)).draw()
        pyglet.text.Label("S / DOWN to change stage", font_size=14, bold=True,
                          x=WINDOW_WIDTH//2, y=sy-33,
                          anchor_x='center', anchor_y='center',
                          color=(0,230,190,255)).draw()

        # Controls hint
        if self.single_player:
            hint = "A/D = select   J = lock   S/DOWN = stage   ENTER = fight"
        else:
            hint = "P1: A/D select  J=lock  |  P2: ←/→ select  1=lock  |  S/DOWN=stage  |  ENTER=fight"
        pyglet.text.Label(hint, font_size=11, x=WINDOW_WIDTH//2, y=28,
                          anchor_x='center', anchor_y='center',
                          color=(180,180,180,190)).draw()

        if self.ready:
            for i in range(5):
                pyglet.shapes.Rectangle(0, 78, WINDOW_WIDTH, 50, color=(0,220,0,45+i*35)).draw()
            label = "PRESS ENTER TO FIGHT!" if self.single_player else "BOTH READY!  PRESS ENTER TO FIGHT!"
            pyglet.text.Label(label, font_size=22, bold=True,
                              x=WINDOW_WIDTH//2, y=103,
                              anchor_x='center', anchor_y='center',
                              color=(0,255,0,255)).draw()


# ══════════════════════════════════════════════════════════════════
#  Global game state
# ══════════════════════════════════════════════════════════════════
game_state      = GameState.INTRO
game_mode       = GameMode.TWO_PLAYER
difficulty      = 1           # 0=easy 1=medium 2=hard
mode_sel_idx    = 0           # cursor on mode-select screen
diff_sel_idx    = 1           # cursor on difficulty screen

char_select     = CharSelect()
fighter1        = None
fighter2        = None
background_sprite = None
key_pressed     = {}

ai              = None        # AI instance (1P mode only)
arcade_sequence = []          # list of char dicts + 'pinata' markers
arcade_idx      = 0
pinata_stage    = None
boss_intro_data = None
boss_intro_t    = 0.0         # countdown timer for boss warning screen

health_bar1_bg  = pyglet.shapes.Rectangle(10,  570, 200, 20, color=(60,0,0))
health_bar2_bg  = pyglet.shapes.Rectangle(590, 570, 200, 20, color=(60,0,0))
health_bar1     = pyglet.shapes.Rectangle(10,  570, 200, 20, color=(0,255,0))
health_bar2     = pyglet.shapes.Rectangle(590, 570, 200, 20, color=(0,255,0))

# ── Joystick ─────────────────────────────────────────────────────
import time as _time  # already imported at top as _time but kept for clarity
JOY_THRESH  = 0.5
_joysticks  = pyglet.input.get_joysticks()
joy1 = _joysticks[0] if len(_joysticks) > 0 else None
joy2 = _joysticks[1] if len(_joysticks) > 1 else None
if joy1: joy1.open(); print(f"Joystick 1: {joy1.device.name}")
if joy2: joy2.open(); print(f"Joystick 2: {joy2.device.name}")

joy1_state = {'x': 0.0, 'y': 0.0, 'buttons': [False] * 12}
joy2_state = {'x': 0.0, 'y': 0.0, 'buttons': [False] * 12}
_joy_nav_cd = {}

def _nav(player, axis, value):
    if abs(value) < JOY_THRESH:
        _joy_nav_cd.pop((player, axis, 'p' if value >= 0 else 'n'), None)
        return
    direction = 'p' if value > 0 else 'n'
    k   = (player, axis, direction)
    now = _time.time()
    if now - _joy_nav_cd.get(k, 0) < 0.25: return
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

def _btn_press(player, button):
    global game_state
    cs = char_select
    if game_state == GameState.INTRO:
        game_state = GameState.MODE_SELECT
    elif game_state == GameState.CHAR_SELECT:
        if player == 1:
            if button == 0 and not cs.p1_locked: cs.p1_locked = True
            elif button in (7,9) and cs.ready:   _start_fight()
        elif player == 2:
            if button == 0 and not cs.p2_locked: cs.p2_locked = True
            elif button in (7,9) and cs.ready:   _start_fight()
    elif game_state == GameState.GAME_OVER:
        if button in (0,7,9): _restart_or_next()

if joy1:
    @joy1.event
    def on_joyaxis_motion(joystick, axis, value):
        if axis == 'x': joy1_state['x'] = value
        elif axis == 'y': joy1_state['y'] = value
        _nav(1, axis, value)
    @joy1.event
    def on_joybutton_press(joystick, button):
        if button < len(joy1_state['buttons']): joy1_state['buttons'][button] = True
        _btn_press(1, button)
    @joy1.event
    def on_joybutton_release(joystick, button):
        if button < len(joy1_state['buttons']): joy1_state['buttons'][button] = False

if joy2:
    @joy2.event
    def on_joyaxis_motion(joystick, axis, value):
        if axis == 'x': joy2_state['x'] = value
        elif axis == 'y': joy2_state['y'] = value
        _nav(2, axis, value)
    @joy2.event
    def on_joybutton_press(joystick, button):
        if button < len(joy2_state['buttons']): joy2_state['buttons'][button] = True
        _btn_press(2, button)
    @joy2.event
    def on_joybutton_release(joystick, button):
        if button < len(joy2_state['buttons']): joy2_state['buttons'][button] = False


# ══════════════════════════════════════════════════════════════════
#  Fighter factory helpers
# ══════════════════════════════════════════════════════════════════
def _load_or_fallback(char_data, fallback_color):
    img = images.get(char_data['image'])
    if not img:
        try:
            img = pyglet.image.load(asset(char_data['image']))
            images[char_data['image']] = img
        except:
            img = pyglet.image.SolidColorImagePattern(fallback_color).create_image(50, 100)
    return img

def make_fighters(c1_data=None, c2_data=None):
    global fighter1, fighter2, background_sprite, batch
    global health_bar1, health_bar2, health_bar1_bg, health_bar2_bg

    batch = pyglet.graphics.Batch()
    if c1_data is None: c1_data = CHARACTERS[char_select.p1]
    if c2_data is None: c2_data = CHARACTERS[char_select.p2]

    img1 = _load_or_fallback(c1_data, (100,100,255,255))
    img2 = _load_or_fallback(c2_data, (200,100,255,255))

    bg_name = STAGES[char_select.stage]['bg']
    bg_img  = images.get(bg_name)
    if bg_img:
        background_sprite = pyglet.sprite.Sprite(bg_img, x=0, y=0, batch=batch)
        background_sprite.scale_x = WINDOW_WIDTH  / bg_img.width
        background_sprite.scale_y = WINDOW_HEIGHT / bg_img.height
    else:
        background_sprite = pyglet.shapes.Rectangle(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT,
                                                    color=(40,30,40), batch=batch)

    fighter1 = Fighter(150, 0, img1, batch,
                       {'left': key.LEFT, 'right': key.RIGHT,
                        'jump': key.UP, 'punch': key.SPACE, 'kick': key.RSHIFT},
                       c1_data, face_right=True)
    fighter2 = Fighter(650, 0, img2, batch,
                       {'left': key.A, 'right': key.D,
                        'jump': key.W, 'punch': key.LSHIFT, 'kick': key.Q},
                       c2_data, face_right=False)

    health_bar1_bg = pyglet.shapes.Rectangle(10,  570, 200, 20, color=(60,0,0))
    health_bar2_bg = pyglet.shapes.Rectangle(590, 570, 200, 20, color=(60,0,0))
    health_bar1    = pyglet.shapes.Rectangle(10,  570, 200, 20, color=(0,255,0))
    health_bar2    = pyglet.shapes.Rectangle(590, 570, 200, 20, color=(0,255,0))


def hbar_color(pct):
    if pct > 0.5: return (0,255,0)
    if pct > 0.25: return (255,165,0)
    return (255,0,0)


# ══════════════════════════════════════════════════════════════════
#  Arcade / 1-player flow control
# ══════════════════════════════════════════════════════════════════
def _start_arcade_fight():
    """Advance to the next item in the arcade sequence."""
    global arcade_idx, game_state, ai, pinata_stage, boss_intro_data, boss_intro_t
    global fighter1, fighter2, batch

    if arcade_idx >= len(arcade_sequence):
        # Cleared the arcade!
        game_state = GameState.GAME_OVER
        stop_music()
        return

    item = arcade_sequence[arcade_idx]
    arcade_idx += 1

    # ── Piñata bonus stage ─────────────────────────────────────
    if item == 'pinata':
        bg = STAGES[char_select.stage]['bg']
        pinata_stage = PinataStage(bg)
        # Need the player fighter for hit detection
        c1 = CHARACTERS[char_select.p1]
        img1 = _load_or_fallback(c1, (100,100,255,255))
        batch = pyglet.graphics.Batch()
        fighter1 = Fighter(200, 0, img1, batch,
                           {'left': key.LEFT, 'right': key.RIGHT,
                            'jump': key.UP, 'punch': key.SPACE, 'kick': key.RSHIFT},
                           c1, face_right=True)
        fighter2 = None
        ai       = None
        game_state = GameState.PINATA
        return

    # ── Boss intro countdown ───────────────────────────────────
    opp_data = item
    if opp_data.get('boss'):
        boss_intro_data = opp_data
        boss_intro_t    = 3.2
        game_state      = GameState.BOSS_INTRO
        stop_music()
        return

    # ── Regular fight ──────────────────────────────────────────
    make_fighters(c1_data=CHARACTERS[char_select.p1], c2_data=opp_data)
    ai = AI(difficulty)
    game_state = GameState.PLAYING
    play_music()


def _launch_boss_fight(boss_data):
    global game_state, ai
    make_fighters(c1_data=CHARACTERS[char_select.p1], c2_data=boss_data)
    ai = AI(2)   # bosses always use max difficulty AI
    game_state = GameState.PLAYING
    play_music()


def _start_fight():
    """Transition from char select to the first fight."""
    global game_state, ai, arcade_sequence, arcade_idx
    if game_mode == GameMode.ARCADE:
        arcade_sequence = make_arcade_sequence(char_select.p1)
        arcade_idx      = 0
        ai              = None
        _start_arcade_fight()
    else:
        make_fighters()
        ai = None
        game_state = GameState.PLAYING
        play_music()


def _restart_or_next():
    """Called after GAME_OVER: rematch in 2P, next fight in Arcade."""
    global game_state
    if game_mode == GameMode.ARCADE:
        _start_arcade_fight()
    else:
        make_fighters()
        game_state = GameState.PLAYING
        play_music()


# ══════════════════════════════════════════════════════════════════
#  Update loop
# ══════════════════════════════════════════════════════════════════
def update(dt):
    global game_state, boss_intro_t, pinata_stage

    # ── Boss intro countdown ─────────────────────────────────────
    if game_state == GameState.BOSS_INTRO:
        boss_intro_t -= dt
        if boss_intro_t <= 0:
            _launch_boss_fight(boss_intro_data)
        return

    # ── Piñata stage ─────────────────────────────────────────────
    if game_state == GameState.PINATA:
        # Player input for piñata stage (movement + attacks)
        if fighter1:
            c = fighter1.controls
            if   key_pressed.get(c['left']):  fighter1.move_left()
            elif key_pressed.get(c['right']): fighter1.move_right()
            else:                              fighter1.stop()
            if key_pressed.get(c['jump']):  fighter1.jump()
            if key_pressed.get(c['punch']): fighter1.punch()
            if key_pressed.get(c['kick']):  fighter1.kick()
            fighter1.update(dt, None)   # no opponent
        pinata_stage.update(dt, fighter1)
        if pinata_stage.done:
            _start_arcade_fight()   # advance to next item
        return

    # ── Regular gameplay ─────────────────────────────────────────
    if game_state != GameState.PLAYING:
        return

    # Player 1 input
    c1 = fighter1.controls
    if   key_pressed.get(c1['left']):  fighter1.move_left()
    elif key_pressed.get(c1['right']): fighter1.move_right()
    else:                               fighter1.stop()
    if key_pressed.get(c1['jump']):  fighter1.jump()
    if key_pressed.get(c1['punch']): fighter1.punch()
    if key_pressed.get(c1['kick']):  fighter1.kick()

    # Joystick P1
    if joy1:
        if joy1_state['x'] < -JOY_THRESH: fighter1.move_left()
        elif joy1_state['x'] >  JOY_THRESH: fighter1.move_right()
        if joy1_state['y'] >  JOY_THRESH or joy1_state['y'] < -JOY_THRESH: fighter1.jump()
        if joy1_state['buttons'][0]: fighter1.punch()
        if joy1_state['buttons'][1]: fighter1.kick()

    # Player 2 / AI input
    if ai:
        ai.update(dt, fighter2, fighter1)
    else:
        c2 = fighter2.controls
        if   key_pressed.get(c2['left']):  fighter2.move_left()
        elif key_pressed.get(c2['right']): fighter2.move_right()
        else:                               fighter2.stop()
        if key_pressed.get(c2['jump']):  fighter2.jump()
        if key_pressed.get(c2['punch']): fighter2.punch()
        if key_pressed.get(c2['kick']):  fighter2.kick()
        # Joystick P2
        if joy2:
            if joy2_state['x'] < -JOY_THRESH: fighter2.move_left()
            elif joy2_state['x'] >  JOY_THRESH: fighter2.move_right()
            if joy2_state['y'] >  JOY_THRESH or joy2_state['y'] < -JOY_THRESH: fighter2.jump()
            if joy2_state['buttons'][0]: fighter2.punch()
            if joy2_state['buttons'][1]: fighter2.kick()

    fighter1.update(dt, fighter2)
    fighter2.update(dt, fighter1)

    # Health bars
    for f, bar in [(fighter1, health_bar1), (fighter2, health_bar2)]:
        pct = f.health / f.max_health
        bar.width = pct * 200
        bar.color = hbar_color(pct)

    # Check KO
    if fighter1.health <= 0 or fighter2.health <= 0:
        game_state = GameState.GAME_OVER
        stop_music()


# ══════════════════════════════════════════════════════════════════
#  Draw loop
# ══════════════════════════════════════════════════════════════════
@window.event
def on_draw():
    window.clear()

    if game_state == GameState.INTRO:
        draw_intro(); return

    if game_state == GameState.MODE_SELECT:
        draw_mode_select(mode_sel_idx); return

    if game_state == GameState.CHAR_SELECT:
        char_select.draw(); return

    if game_state == GameState.DIFFICULTY_SELECT:
        draw_difficulty_select(diff_sel_idx); return

    if game_state == GameState.BOSS_INTRO:
        draw_boss_intro(boss_intro_data, boss_intro_t); return

    if game_state == GameState.PINATA:
        pinata_stage.draw()
        if fighter1:
            batch.draw()           # draw player sprite on top of pinata stage
        return

    # PLAYING or GAME_OVER — draw the fight scene
    if fighter1 and fighter2:
        batch.draw()

        # Character name labels
        pyglet.text.Label(fighter1.char_data['name'], font_size=12,
                          x=15, y=594, color=(200,200,255,255)).draw()
        pyglet.text.Label(fighter2.char_data['name'], font_size=12,
                          x=785, y=594, anchor_x='right',
                          color=(255,200,200,255)).draw()

        # Boss label badge
        if fighter2.char_data.get('boss'):
            pyglet.shapes.Rectangle(590, 560, 200, 14, color=(120,0,0,200)).draw()
            pyglet.text.Label("BOSS", font_size=10, bold=True,
                              x=690, y=567, anchor_x='center', anchor_y='center',
                              color=(255,80,80,255)).draw()
        if game_mode == GameMode.ARCADE:
            fight_num = arcade_idx
            pyglet.text.Label(f"FIGHT {fight_num} / {len(arcade_sequence)}",
                              font_size=11, x=WINDOW_WIDTH//2, y=592,
                              anchor_x='center', anchor_y='center',
                              color=(200,200,200,200)).draw()

        health_bar1_bg.draw(); health_bar1.draw()
        health_bar2_bg.draw(); health_bar2.draw()

    if game_state == GameState.GAME_OVER:
        pyglet.shapes.Rectangle(0,0,WINDOW_WIDTH,WINDOW_HEIGHT,color=(0,0,0,160)).draw()

        if game_mode == GameMode.ARCADE and arcade_idx >= len(arcade_sequence):
            # Player cleared arcade mode!
            pyglet.text.Label("YOU WIN!", font_size=56, bold=True,
                              x=WINDOW_WIDTH//2, y=WINDOW_HEIGHT//2+50,
                              anchor_x='center', anchor_y='center',
                              color=(255,215,0,255)).draw()
            pyglet.text.Label("ARCADE MODE COMPLETE!",
                              font_size=26, x=WINDOW_WIDTH//2, y=WINDOW_HEIGHT//2,
                              anchor_x='center', anchor_y='center',
                              color=(200,255,200,255)).draw()
            pyglet.text.Label("ENTER = play again   ESC = menu",
                              font_size=18, x=WINDOW_WIDTH//2, y=WINDOW_HEIGHT//2-60,
                              anchor_x='center', anchor_y='center',
                              color=(200,200,200,220)).draw()
        elif fighter1 and fighter2:
            if fighter2.health == 0 and game_mode == GameMode.ARCADE:
                # Won this fight, more to come
                pyglet.text.Label("VICTORY!", font_size=52, bold=True,
                                  x=WINDOW_WIDTH//2, y=WINDOW_HEIGHT//2+30,
                                  anchor_x='center', anchor_y='center',
                                  color=(255,215,0,255)).draw()
                pyglet.text.Label("PRESS ENTER TO CONTINUE",
                                  font_size=20, x=WINDOW_WIDTH//2, y=WINDOW_HEIGHT//2-40,
                                  anchor_x='center', anchor_y='center',
                                  color=(200,200,200,230)).draw()
            elif fighter1.health == 0 and game_mode == GameMode.ARCADE:
                pyglet.text.Label("GAME OVER", font_size=52, bold=True,
                                  x=WINDOW_WIDTH//2, y=WINDOW_HEIGHT//2+30,
                                  anchor_x='center', anchor_y='center',
                                  color=(255,50,50,255)).draw()
                pyglet.text.Label("ENTER = try again   ESC = menu",
                                  font_size=18, x=WINDOW_WIDTH//2, y=WINDOW_HEIGHT//2-50,
                                  anchor_x='center', anchor_y='center',
                                  color=(200,200,200,220)).draw()
            else:
                winner = fighter1.char_data['name'] if fighter2.health == 0 else fighter2.char_data['name']
                pyglet.text.Label(f"{winner} WINS!", font_size=48, bold=True,
                                  x=WINDOW_WIDTH//2, y=WINDOW_HEIGHT//2+30,
                                  anchor_x='center', anchor_y='center',
                                  color=(255,215,0,255)).draw()
                pyglet.text.Label("ENTER = rematch    ESC = character select",
                                  font_size=18, x=WINDOW_WIDTH//2, y=WINDOW_HEIGHT//2-45,
                                  anchor_x='center', anchor_y='center',
                                  color=(200,200,200,255)).draw()


# ══════════════════════════════════════════════════════════════════
#  Key handlers
# ══════════════════════════════════════════════════════════════════
@window.event
def on_key_press(symbol, modifiers):
    global game_state, game_mode, mode_sel_idx, diff_sel_idx, char_select

    key_pressed[symbol] = True

    # ── INTRO ────────────────────────────────────────────────────
    if game_state == GameState.INTRO:
        if symbol == key.ENTER:
            game_state = GameState.MODE_SELECT
        return

    # ── MODE SELECT ──────────────────────────────────────────────
    if game_state == GameState.MODE_SELECT:
        if symbol in (key.UP, key.W):
            mode_sel_idx = (mode_sel_idx - 1) % 2
        elif symbol in (key.DOWN, key.S):
            mode_sel_idx = (mode_sel_idx + 1) % 2
        elif symbol == key.ENTER:
            if mode_sel_idx == 0:
                game_mode    = GameMode.ARCADE
                diff_sel_idx = 1          # reset difficulty cursor to Medium
                game_state   = GameState.DIFFICULTY_SELECT
            else:
                game_mode   = GameMode.TWO_PLAYER
                char_select = CharSelect(single_player=False)
                game_state  = GameState.CHAR_SELECT
        elif symbol == key.ESCAPE:
            game_state = GameState.INTRO
        return

    # ── DIFFICULTY SELECT ────────────────────────────────────────
    if game_state == GameState.DIFFICULTY_SELECT:
        if symbol in (key.UP, key.W):
            diff_sel_idx = (diff_sel_idx - 1) % 3
        elif symbol in (key.DOWN, key.S):
            diff_sel_idx = (diff_sel_idx + 1) % 3
        elif symbol == key.ENTER:
            global difficulty
            difficulty  = diff_sel_idx
            char_select = CharSelect(single_player=True)
            game_state  = GameState.CHAR_SELECT
        elif symbol == key.ESCAPE:
            game_state = GameState.MODE_SELECT
        return

    # ── CHAR SELECT ──────────────────────────────────────────────
    if game_state == GameState.CHAR_SELECT:
        cs = char_select
        if not cs.p1_locked:
            if symbol == key.A:   cs.p1 = (cs.p1 - 1) % len(CHARACTERS)
            elif symbol == key.D: cs.p1 = (cs.p1 + 1) % len(CHARACTERS)
            elif symbol == key.J: cs.p1_locked = True
        if not cs.p2_locked and game_mode == GameMode.TWO_PLAYER:
            if symbol == key.LEFT:   cs.p2 = (cs.p2 - 1) % len(CHARACTERS)
            elif symbol == key.RIGHT: cs.p2 = (cs.p2 + 1) % len(CHARACTERS)
            elif symbol == key._1:    cs.p2_locked = True
        if symbol in (key.S, key.DOWN):
            cs.stage = (cs.stage + 1) % len(STAGES)
        if symbol == key.ENTER and cs.ready:
            _start_fight()
        if symbol == key.ESCAPE:
            game_state = GameState.MODE_SELECT
        return

    # ── GAME OVER ────────────────────────────────────────────────
    if game_state == GameState.GAME_OVER:
        if symbol == key.ENTER:
            if game_mode == GameMode.ARCADE and fighter1 and fighter2 and fighter1.health == 0:
                # Lost — restart arcade from beginning
                global arcade_idx
                arcade_idx = 0
                _start_arcade_fight()
            elif game_mode == GameMode.ARCADE and arcade_idx >= len(arcade_sequence):
                # Cleared arcade — go back to menu
                game_state = GameState.INTRO
            else:
                _restart_or_next()
        elif symbol == key.ESCAPE:
            stop_music()
            game_state  = GameState.MODE_SELECT
            char_select = CharSelect(single_player=(game_mode == GameMode.ARCADE))
        return

    # ── PINATA (ESC to skip bonus) ───────────────────────────────
    if game_state == GameState.PINATA:
        if symbol == key.ESCAPE:
            pinata_stage.done = True
        return

@window.event
def on_key_release(symbol, modifiers):
    key_pressed[symbol] = False


print("Starting game loop")
pyglet.clock.schedule_interval(update, 1/60.0)
pyglet.app.run()
print("Game loop ended")
