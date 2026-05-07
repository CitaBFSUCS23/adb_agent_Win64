# Skill: Elderly Mode Setup

## Description
Complete phone setup suitable for elderly users in one go: larger font size, higher DPI, adjust display scaling, increase volume.

## Preconditions
- Device is connected and in debugging mode
- Requires Root or ADB Shell permissions (some settings need this)

## Steps

### Step 1: Increase font scale
Set font scale to 1.3x (or larger):
```
shell settings put system font_scale 1.3
```

### Step 2: Adjust DPI
Increase DPI to make interface elements larger (e.g., from 440 to 520):
```
shell wm density 520
```
Recommended values: 480, 520, 560 (larger number = larger interface)

### Step 3: Adjust display scaling (optional)
Adjust display scaling:
```
shell settings put global window_animation_scale 1.0
shell settings put global transition_animation_scale 1.0
shell settings put global animator_duration_scale 1.0
```

### Step 4: Increase volume
Set media volume, call volume, and ringtone volume to higher levels:
```
# Media volume (0-15)
shell media volume --stream 3 --set 12
# Call volume (0-7)
shell media volume --stream 0 --set 6
# Ringtone volume (0-7)
shell media volume --stream 2 --set 6
```
Or use:
```
# Get current volume
shell cmd media volume --stream 3 --get
# Set volume
shell cmd media volume --stream 3 --set 12
```

### Step 5: Other optional optimizations (as needed)
- Enable large font mode
- Disable animations
- Enable simple mode (if device supports it)

### Step 6: Verify settings
Check current settings:
```
shell settings get system font_scale
shell wm density
```

## Tips
- Font scale suggestions: 1.2, 1.3, 1.5 (don't make too big to avoid UI issues)
- DPI suggestions: Adjust based on original device DPI, usually increase by 20-30%
- If DPI setting causes UI issues, reset to default:
  ```
  shell wm density reset
  ```
- Maximum volume levels: Media 15, Call 7, Ringtone 7