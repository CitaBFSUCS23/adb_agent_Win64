# Skill: Screen Operations (Vision Mode)

## Description
Control Android device by reading the screen via vision AI. Always look before acting — like a human operator.

## Core Principle: Look → Think → Act → Verify
NEVER execute a tap, swipe, or text input without first seeing the screen. After each action, verify the result.

## Commands Reference

### Screen Tools
```
screen_tool  describe        → Full screen description (icons, buttons, coordinates)
screen_tool  find <目标>     → Find specific element, returns exact coordinates
screen_tool  check           → Quick check of current app/screen
```

### Touch Commands (via adb_tool)
```
shell input tap X Y           → Single tap at coordinates
shell input swipe X1 Y1 X2 Y2 [ms]  → Swipe/scroll
shell input swipe X Y X Y 1000      → Long press (1 second)
shell input text "text"       → Type text (ensure field is focused first)
shell input keyevent KEYCODE  → Press key (HOME=3, BACK=4, ENTER=66)
```

## Step-by-Step Workflow

### Step 1: See the screen
Always start by calling screen_tool.describe to understand the current screen.

### Step 2: Plan the action
Based on the screen description, decide which element to interact with using its pixel coordinates.

### Step 3: Execute
Call adb_tool with the appropriate tap/swipe command using the coordinates from Step 1.

### Step 4: Verify
Call screen_tool.describe again to confirm the action had the expected effect. If not, adjust coordinates (±20px) or try swiping.

### Step 5: Repeat or complete
Continue until the user's task is achieved.

## Common Patterns

### Pattern 1: Open an app
1. `screen_tool.describe` → see home screen with icons
2. Find the app icon coordinates
3. `adb_tool: shell input tap X Y` → tap the icon
4. `screen_tool.check` → verify app opened

### Pattern 2: Search for something
1. `screen_tool.describe` → see app screen
2. Find search bar coordinates
3. `adb_tool: shell input tap X Y` → tap search bar
4. `adb_tool: shell input text "search terms"` → type query
5. `adb_tool: shell input keyevent 66` → press Enter
6. `screen_tool.describe` → see search results

### Pattern 3: Scroll to find element
1. `screen_tool.find <element>` → if not found on current screen
2. `adb_tool: shell input swipe 540 1500 540 500 500` → scroll up
3. `screen_tool.find <element>` → try again

### Pattern 4: Open notification / quick settings
1. `adb_tool: shell input swipe 540 0 540 800 300` → pull down from top
2. `screen_tool.describe` → see notifications/quick settings
3. Find and tap the desired toggle (GPS, WiFi, etc.)

## Coordinate System
- Screen origin: top-left corner (0, 0)
- Typical screen: 1080×2400 pixels
- Center of screen: (540, 1200)
- Status bar: top ~100px
- Navigation bar: bottom ~150px
- For scrollable content, the visible area and element positions may shift after scrolling

## Error Recovery
- If a tap at (X,Y) doesn't work, try (X±20, Y±20)
- If text input didn't work, the field might not be focused — tap it again first
- If the expected screen didn't appear, call screen_tool.describe to see the actual state
- If stuck, try pressing BACK (keyevent 4) and restart from Step 1
- After 3 failed attempts at the same action, try a different approach or ask the user

## Important Notes
- NEVER assume coordinates — always get them from screen_tool
- Each screen_tool call uses the vision model, so plan actions efficiently
- The model can see: text, icons, buttons, images, and their positions
- The model CANNOT see: hidden elements, scrollable content beyond visible area
- Chinese UI elements: the model understands Chinese text on screen
