#!/usr/bin/env python3
import re

with open('main_game.py', 'r') as f:
    content = f.read()

# Find and replace CHARACTERS list
new_characters = '''CHARACTERS = [
    {'name': 'Shadow',    'image': 'blue_ninja.png',    'speed': 300, 'power': 1.0, 'health': 100, 'scale': 0.5},
    {'name': 'Blaze',     'image': 'purple_ninja.png',  'speed': 260, 'power': 1.4, 'health': 90,  'scale': 0.5},
    {'name': 'Frost',     'image': 'blue_ninja.png',    'speed': 350, 'power': 0.8, 'health': 110, 'scale': 0.45},
    {'name': 'Venom',     'image': 'purple_ninja.png',  'speed': 240, 'power': 1.6, 'health': 85,  'scale': 0.55},
    {'name': 'Storm',     'image': 'blue_ninja.png',    'speed': 400, 'power': 0.7, 'health': 120, 'scale': 0.42},
    {'name': 'Slime',     'image': 'slime_buddy.png',   'speed': 200, 'power': 0.8, 'health': 130, 'scale': 0.6},
    {'name': 'Dino',      'image': 'robo_dino.png',     'speed': 250, 'power': 1.8, 'health': 110, 'scale': 0.7},
]'''

# Replace the CHARACTERS section
pattern = r'CHARACTERS = \[[^\]]*\]'
content = re.sub(pattern, new_characters, content, flags=re.DOTALL)

# Remove Capitol Clash from STAGES
new_stages = '''STAGES = [
    {'name': 'Dojo',        'bg': 'background.png'},
    {'name': 'Waffles Haus', 'bg': 'waffles_haus_bg.png'},
    {'name': 'Battle Arena', 'bg': 'battle_arena_bg.png'},
]'''

pattern = r'STAGES = \[[^\]]*\]'
content = re.sub(pattern, new_stages, content, flags=re.DOTALL)

# Remove Capitol Clash from STAGE_TINTS
new_tints = '''STAGE_TINTS = [
    (255, 255, 255),   # Dojo - normal
    (255, 220, 180),   # Waffles Haus - warm golden
    (200, 200, 255),   # Battle Arena - blue/cool
]'''

pattern = r'STAGE_TINTS = \[[^\]]*\]'
content = re.sub(pattern, new_tints, content, flags=re.DOTALL)

with open('main_game.py', 'w') as f:
    f.write(content)

print("Updated characters and stages!")
print("Characters:", [c['name'] for c in eval(new_characters[14:])])
print("Stages:", [s['name'] for s in eval(new_stages[10:])])
