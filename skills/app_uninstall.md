# Skill: App Uninstall

## Description
Find package name by app name, then uninstall the app.

## Preconditions
- Device is connected and in debugging mode
- App to uninstall is installed

## Steps

### Step 1: Get app list
Execute command to get all installed apps:
```
shell pm list packages
```
Parse results to get all package names.

### Step 2: Get app labels (optional, for better matching)
For more precise matching, get app labels:
```
shell pm list packages -f
```

### Step 3: Find package name by app name
Use Python script for fuzzy matching:
```python
import re
apps_output = """
package:com.android.settings
package:com.example.app
"""
target_name = "settings"  # User input app name

# Parse package list
packages = [line.replace("package:", "").strip() 
           for line in apps_output.split("\n") 
           if line.startswith("package:")]

# Simple match: check if package contains keywords from target name
# Can also try getting app labels via dumpsys for better matching
matched = []
for pkg in packages:
    if target_name.lower() in pkg.lower():
        matched.append(pkg)

print("Found packages:", matched)
```

### Step 4: Confirm package name
If matching packages are found, confirm with user. If multiple found, let user choose.

### Step 5: Uninstall app
Execute uninstall command:
```
uninstall <package_name>
```
Or keep data:
```
shell pm uninstall -k <package_name>
```

### Step 6: Complete
Confirm uninstall successful.

## Tips
- If user says "uninstall WeChat", try to find packages containing "wechat"
- Common app package names:
  - WeChat: com.tencent.mm
  - QQ: com.tencent.mobileqq
  - Alipay: com.eg.android.AlipayGphone
  - TikTok: com.ss.android.ugc.aweme
  - Taobao: com.taobao.taobao
- If no precise match found, can list all apps for user to choose