#!/bin/bash

echo "=== Processing Waffle House Images ==="

# Convert webp to png first
for f in ~/Downloads/preview*.webp; do
    name=$(basename "$f" .webp)
    dwebp "$f" -o "${name}.png" 2>/dev/null
done

# Copy the Waffle House image (preview 5)
cp "preview (5).png" waffle_original.png 2>/dev/null

# Remove text from bottom but keep the building
# Crop out the bottom text area (y: 0-540 keeps building, removes bottom text)
convert waffle_original.png -crop 800x540+0+0 +repage waffle_cropped.png

# Add a subtle "Waffles Haus" watermark in the corner (small, classy)
convert waffle_cropped.png -font Arial -pointsize 20 -fill "rgba(255,215,0,0.4)" \
    -annotate +20+20 "Waffles Haus" waffle_stage.png

# Create a clean background for the game
cp waffle_stage.png waffles_haus_bg.png

# Also create a smaller logo/icon for character select
convert waffle_cropped.png -resize 120x80 -font Arial -pointsize 14 -fill "rgba(255,215,0,0.5)" \
    -annotate +5+15 "Waffles Haus" waffles_haus_icon.png

# Process preview (8) - Kirby Battle Blitz
if [ -f "preview (8).png" ]; then
    convert "preview (8).png" -crop 800x560+0+0 +repage kirby_cropped.png
    convert kirby_cropped.png -font Arial -pointsize 16 -fill "rgba(255,215,0,0.3)" \
        -annotate +10+20 "Battle Arena" kirby_stage.png
    cp kirby_stage.png battle_arena_bg.png
fi

# Process preview (6) - Democrat/Republican (political theme)
if [ -f "preview (6).png" ]; then
    convert "preview (6).png" -crop 800x540+0+0 +repage political_cropped.png
    convert political_cropped.png -font Arial -pointsize 16 -fill "rgba(255,215,0,0.3)" \
        -annotate +10+20 "Capitol Clash" capitol_clash_bg.png
fi

echo "=== Done! ==="
echo "Created:"
ls -lh waffles_haus_bg.png battle_arena_bg.png capitol_clash_bg.png 2>/dev/null
