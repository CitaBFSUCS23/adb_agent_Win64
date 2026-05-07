# Skill: Photo Export

## Description
Export photos from Android device to computer, supports sorting by time and selecting number of photos.

## Preconditions
- Device is connected and in debugging mode
- Photos are usually in /sdcard/DCIM/Camera/ directory

## Steps

### Step 1: List photos
Execute command to view latest photos:
```
shell ls -lt /sdcard/DCIM/Camera/
```
Parse the photo list, sorted by time (latest first).

### Step 2: Select number of photos
Determine how many photos to export based on user request (default: latest 10).

### Step 3: Create local directory (optional)
If local directory doesn't exist, use Python to create it:
```
import os
os.makedirs("./exported_photos", exist_ok=True)
```

### Step 4: Export photos one by one
Use pull command to export each photo:
```
pull /sdcard/DCIM/Camera/photo1.jpg ./exported_photos/
pull /sdcard/DCIM/Camera/photo2.jpg ./exported_photos/
```

### Step 5: Complete
After export completes, inform user where photos are saved.

## Tips
- If user says "export photos", default to latest 10
- If user specifies number, export that number
- Support other photo directories: /sdcard/Pictures/, /sdcard/DCIM/Screenshots/
- Common photo extensions: .jpg, .jpeg, .png, .mp4