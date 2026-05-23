# Android Device Automation Control System Based on ADB and Multi-Agent Collaboration

## Abstract
This project designs and implements an Android device automation control and intelligent assistance platform. Built on ADB (Android Debug Bridge) with integrated scrcpy for low-latency screen mirroring, it provides traditional control functions including device management, application control, script automation, and battery simulation. We introduce task-oriented intelligent agents based on Large Language Models (LLMs), using the ReAct decision loop for complex task decomposition and execution. Furthermore, we design a Multi-Agent Collaboration (Agent Corp) architecture, splitting responsibilities like visual analysis and command execution into independent sub-agents that collaborate through asynchronous messaging to complete long-chain mobile operation tasks. The system uses tkinter for desktop GUI with multi-language support. All tools and skills are implemented based on a plugin architecture with excellent extensibility.

## I. Problem Analysis and Scenario Definition

### 1. Problem Background
As smartphone functions become increasingly complex, many frequent operations present high barriers for specific user groups:
- Elderly users struggle with multi-step operations like enabling GPS, using maps, or sending locations
- Test engineers need to repeat fixed regression test processes across multiple devices
- People with disabilities may be unable to interact with devices through conventional touch methods

Traditional PC-side Android management tools (like manufacturer assistants) often only provide basic information display and file transfer, lacking automation support for complex tasks and natural language interaction capabilities. While ADB provides comprehensive device control interfaces, its command-line form is extremely unfriendly to ordinary users.

### 2. Application Scenarios
- **Intelligent Assistance**: Users describe tasks in natural language (e.g., "Send the most recent photo to WeChat friend Zhang San"), and the system autonomously plans and executes the complete operation chain
- **Remote Assistance**: Technical personnel view the user's device screen in real-time through scrcpy and issue repair commands in conjunction with Agent
- **Automated Testing**: Record and replay ADB scripts, combined with AI dynamic decision-making to handle non-deterministic UI changes
- **Elderly-Friendly Transformation**: One-click execution of preset skills (e.g., Elderly Mode Setup) to adjust fonts, disable redundant notifications, and pin commonly used apps to the desktop

### 3. Target Users
- Elderly users unfamiliar with technical operations
- Developers and testers needing to operate multiple devices in batches
- People with disabilities who wish to indirectly control phones through voice/text
- Academic researchers studying edge-side device control and embodied intelligence

## II. System Architecture Design

The system adopts a layered architecture, from bottom to top: Device Control Layer, Traditional GUI Layer, and Agent Layer.

### 1. Device Control Layer
This layer directly interfaces with Android devices, relying on ADB and scrcpy protocols:
- **ADBClient**: Encapsulates adb.exe calls, supporting shell command execution, file push/pull, APK installation/uninstallation, port forwarding, etc.
- **scrcpy**: Uses its server-client architecture to render the device screen on PC, enabling real-time screen mirroring and reverse control (click, swipe mapping)
- **Key Injection**: Simulates physical keys (Home, Back, Volume, Power) through adb shell input keyevent

### 2. Traditional GUI Layer
Built with tkinter as a multi-tab desktop application, with the following page responsibilities:
- **Home Page**: Device discovery and selection, real-time hardware information display (model, Android version, CPU, memory, battery)
- **Software Page**: Installed application list (system/third-party filtering), enable/disable, APK export, clear data, uninstall
- **Display Page**: View and modify resolution and DPI settings, supporting override reset
- **Battery Page**: Battery status monitoring, simulate AC/USB charging, custom battery percentage
- **Script Page**: Visual ADB script editor, supporting button panel, delay nodes, variable templates, JSON persistent storage
- **Agent Page**: AI agent interaction interface, supporting API configuration, session management, command confirmation (Execute/Reject/Stop)

In terms of performance optimization, this layer uses a multi-threaded architecture: all ADB operations execute in background threads, UI updates safely through Tkinter's `after()` mechanism; independent commands within the same page are submitted in parallel (e.g., Home page issues 11+ getprop commands simultaneously), significantly reducing interface loading latency.

### 3. Agent Layer
This is the core innovation of the project, drawing on OpenClaw architecture concepts, divided into three sub-layers:

#### (1) Tools Layer
The abstract base class `BaseTool` defines a unified interface (`execute`, `get_prompt_section`). New tools only need to inherit and place in the `tools/` directory to be automatically discovered.

#### (2) Skills Layer
Skills are stored as Markdown documents in the `skills/` directory, containing task descriptions, preconditions, and step-by-step guides. Agents automatically retrieve relevant skills and inject them into context during the planning phase, reducing reliance on the model's general knowledge. Existing skills include Photo Export, App Uninstall, Elderly Mode Configuration, etc.

#### (3) Agent Runtime
- **StandaloneAgent (Solo Mode)**: Single agent directly interacting with users, adopting ReAct loop (Reason → Action → Observation), supporting three response types: Thought/Command/Final
- **Agent Corp (Multi-Agent Mode)**: Splits responsibilities into sub-agents like VisionAgent (screen perception and coordinate positioning) and ExecutorAgent (ADB command execution). User messages are dispatched to sub-agents through the runtime scheduler, which can further request assistance from other sub-agents, forming an asynchronous collaboration network. Corp mode enables "auto-execute" by default and disables "chat-only" to ensure the task chain can be completed closed-loop.

#### (4) Memory Layer
File-system-based session management: Each conversation is saved as JSON in the `history/` directory, supporting multi-round context loading, session title renaming, and deletion. To control context length, the runtime automatically compresses historical messages when exceeding thresholds.

## III. Technical Implementation Path

### 1. scrcpy Low-Latency Screen Mirroring Integration
scrcpy pushes scrcpy-server to the device through ADB, establishing a local Socket connection to transmit H.264 video streams and input events. This project packages scrcpy.exe and its dependent DLLs in the `dependencies/` directory. The GUI launches an independent screen mirroring window through `subprocess.Popen`, supporting auxiliary functions like always-on-top and screenshot capture. The screen mirroring window is decoupled from the main interface, allowing users to close or reopen it at any time.

### 2. ReAct Decision Loop and Response Parsing
In single-agent mode, the system concatenates the system prompt, available tool descriptions, skill documents, and user input into a complete context sent to the LLM. The model's returned text is parsed into structured fields through regular expressions:
- **Thought**: The agent's reasoning process (shown to users to enhance interpretability)
- **Command**: The specific command to execute (e.g., `ADBTOOL: input tap 500 800`)
- **Final**: The summary response when the task is complete

The parser also detects dangerous command patterns (rm, reboot, factory reset, etc.) and wraps them in warning boxes in the GUI to prompt user confirmation.

### 3. Multi-Agent Message Routing
The Agent Runtime maintains a sub-agent registry. In Corp mode:
1. User input is first passed to Agent Leader
2. Agent Leader dispatches subtasks to specialized agents based on task steps
3. If a sub-agent needs to use another sub-agent's expertise, it forwards the request through the runtime
4. All sub-agents' Thoughts and execution results are reported back to Agent Leader
5. Agent Leader outputs the Complete identifier and presents the result to the user when task completion is determined

This mechanism avoids the problem of model attention dispersion caused by a single prompt carrying too many responsibilities.

### 4. Plugin-Based Tools and Skills Auto-Discovery
- **Tool Discovery**: Scans the `tools/` directory on application startup, imports all BaseTool subclasses, builds a name → class mapping dictionary. Tool authors do not need to modify any framework code
- **Skill Discovery**: Scans .md files in the `skills/` directory, parses YAML-like header metadata, dynamically injects skill context based on keyword relevance to user queries at runtime

### 5. Internationalization (i18n)
Language packs are stored as JSON key-value pairs in the `language/` directory. The main interface dynamically replaces text based on the current language setting through the global `tr()` function. When switching languages, it iterates through all registered translatable controls (Label, Button, Checkbutton, etc.) and updates them in real-time without requiring application restart.

## IV. Experiment and Evaluation

| Task | Purpose | Observation | Evaluation |
|------|---------|-------------|------------|
| USB Wired Debugging | Check basic ADB functionality | All page buttons execute normally | Device control layer passes test |
| LAN Wireless Debugging | Check wireless debugging feature | All page buttons execute normally | Wireless debugging works correctly |
| Screen Mirroring in Dual Modes | Check screen mirroring and control functionality | Response is good. Wired latency within 30ms, wireless latency around 100ms. Mouse directly operates Android device on PC screen | Screen mirroring is fast, accurate, and stable. Window size adapts well to different screen sizes |
| Language Switching | Check GUI response | Global language updates immediately without software restart | GUI language switching adapts well |
| Control Script Testing | Check script functionality | Write a normal process script for group SMS in TIM (chat app). After writing, tested successfully on development machine; no point testing on other devices | Limitation of traditional ADB scripts: operations highly dependent on each device's settings. When changing devices, adjusting DPI, app arrangement, or controlled software's operation logic updates, old scripts become meaningless. But proves that traditional method of defining ADB operation sequences is feasible |
| Agent Testing: API Import/Export/Test | Check external API calling, configuration save and load logic | When configuration is incorrect, responds "API disconnected", cannot complete task. When configuration succeeds, testing API shows "API connected". Import/export of API configuration saved as disk file works normally | Agent configuration area's three input boxes and three buttons work correctly |
| Agent SOLO Mode: Mute Phone | Single-step, verify functionality | Task completed. Correctly executed adb command | Most basic natural language debugging. Agent detected it could use adb_tool and successfully called it |
| Agent SOLO Mode: Export 4 most recent photos to PC | Multi-step. Single adb command cannot complete this task. Should first find camera photo storage location, list directory files chronologically, create folder with python, import files using pull command | Agent completed work without any prompts. However, after finding 4 most recent photos, Agent manually constructed 4 pull commands, importing them one by one. Tester suggested: should write python script automatically receiving adb pm list output, loop auto-exporting photos. After prompt, Agent completed work as guided | Agent has multi-step planning capability, tool output monitoring capability (otherwise wouldn't know which 4 photos were most recent). Its autonomous planning didn't comprehensively use both tools for full automation, but used them independently. Requires monitoring list output and constructing adb pull commands based on list results, has ReAct capability to adjust strategy based on output |
| Agent Corp Mode: Swap all photos from QQ and WeChat | Multi-agent testing | Agent Leader dispatched two Executor Agents to find paths of two target folders in parallel, two sub-agents each backed up their managed folders to temp, Leader issued coordination commands swapping files through temp folder. Finally Leader outputs Complete indicating task done | Multi-agent test passes, but not optimal path. Actually could swap directly by renaming both folders, no need to actually swap photo files themselves through temp folder. Should consider allowing Leader to dismiss (destroy) sub-agents at any time and pivot promptly |
| Agent Testing: Stop | Terminate task before conversation completes | Tasks stop within 3s (SOLO, Corp). No subsequent output because user force stopped | Prevents AI from falling into output loop wasting Token |
| Agent Page Testing | Session rename, delete, memory rollback etc. | Disk file updates successful, GUI info updates in real-time | Gives users freedom to manage their sessions |
| Agent Testing: Skill | In SOLO mode, "Adjust device to elderly mode", where Skill directory contains prompts for settings elderly should make | Agent understood task and matched to relevant skill in Skill directory. Autonomously chose to spend an extra step reading Skill body. After reading, completed task as Skill instructed | To avoid hallucinations, tester intentionally wrote an incorrect instruction in corresponding Skill for adjusting DPI to zoom screen and font. Skill intentionally wrote wrong direction for DPI adjustment, and Agent indeed adjusted in wrong direction. Shows Agent actually utilized Skill |
| Agent Testing: Multi-Round Conversation | Initial: Export QQ saved photos to exported_pics folder named {number}.{format}; Continue: Do same for WeChat saved images in same folder continuing numbering | Agent completed task. Created exported_pics folder using Python, exported total 6 (QQ)+7 (WeChat)=13 photos from test device, file naming matched required format, correct numbering | Second-round conversation contained previous instructions like "same operation", "same folder", "continue numbering". Proves Agent memory architecture implemented well—otherwise Agent shouldn't understand these instructions |

**Table 1: Test Cases**

**Note**: Base models used for testing: Text model Deepseek v4-flash (Deepseek official API), multimodal model Qwen3.6 thinking=false (Alibaba Cloud Bailian Platform API)

## V. Discussion and Reflection

### 1. Innovations
- **Gradual Evolution from Traditional ADB Tools to AI Agents**: This project does not merely provide a conversational robot, but deeply integrates agents into existing device management workflows while preserving all traditional GUI functions, reducing user migration cost
- **Multimodal Perception and Execution Closed-Loop**: Through scrcpy screen mirroring + VisionAgent screen analysis, for the first time achieves a human-like phone operation chain of "observe screen → understand interface → tap precisely", breaking through the limitations of pure text ADB commands on dynamic UIs
- **Open Plugin Architecture**: Both Tools Layer and Skills Layer support zero-code-intrusion extension, possessing excellent community collaboration potential

### 2. Limitations
- **Visual Coordinate Dependency**: Current VisionAgent relies on the vision capability of large models to return coordinates. Positioning accuracy may decrease on low-resolution screens, complex dynamic interfaces, or game scenarios
- **Context Compression Loss**: Historical messages are automatically compressed during long task execution, potentially causing early critical constraints to be forgotten
- **Limited Exception Recovery**: When ADB commands fail (e.g., tap coordinates out of screen, app not responding), Agent primarily relies on LLM's own reasoning for retries, lacking system-level exception rollback mechanisms
- **Network Dependency**: Multi-round LLM calls in Corp mode have higher requirements for network stability, with noticeable latency in weak network environments

### 3. Risks and Ethical Issues
This project has the capability to directly control physical devices, therefore the following risks must be addressed during design and usage:

#### (1) Remote Control and Privacy Violation
The system can connect to any device with debugging mode enabled in the LAN through WiFi ADB. If maliciously deployed, an attacker can take screenshots, read SMS, install apps, even access the camera, and fully control the device without the owner's knowledge. This constitutes a serious invasion of private digital spaces.

#### (2) Automated Fraud and Phishing
Agents can automatically open banking apps, read verification codes, and perform transfer operations. If combined with social engineering rhetoric generated by large models, it could form highly automated telecommunication fraud tools, significantly lowering the technical barrier for crime.

#### (3) Reverse Abuse of Accessibility Features
One of the project's original intentions is to help people with disabilities and elderly users, but the same automation capability can be used for black-gray industry practices like bulk fake account registration, auto-botting, automated harassment (e.g., looping messages), etc.

#### (4) Data Leakage Risk
- API configuration (URL, Key) is stored in plain text in local files, which may lead to large model API keys being stolen if the device is shared or suffers from Trojan attacks
- Session history is stored in plain text JSON, containing complete user-Agent conversations that may leak sensitive personal information

#### (5) Responsibility Attribution Dilemma
When an agent autonomously decides and executes destructive operations (e.g., deleting important data by mistake, accidentally dialing emergency calls, posting inappropriate content on social platforms), responsibility should belong to the model provider, system developer, or end-user? Currently, clear legal and technical traceability mechanisms are lacking.

#### (6) Surveillance and Labor Control
In enterprise management or family guardianship scenarios, this system could be transformed into a covert monitoring tool, continuously recording screen activities and operation trajectories of employees or family members, raising serious ethical concerns.

#### (7) Amplification of Model Bias
The LLM relied upon by agents may carry training data biases (e.g., unfamiliarity with apps from specific regions, deviation in understanding non-English interfaces), potentially giving inappropriate operations in cross-cultural scenarios.

### 4. Mitigation Measures and Future Directions
- Introduce local secondary confirmation for sensitive operations (e.g., transfers, uninstalling system apps, modifying system settings require manual confirmation)
- Encrypt API keys and session history storage
- Add operation audit logs recording executor, time, and result of each ADB command
- Explore edge-side small model deployment to reduce data transmission
- Establish clear usage authorization mechanisms (e.g., only allow connection to paired devices)

## VI. Appendix

- Project is open-sourced at https://github.com/CitaBFSUCS23/adb_agent_Win64
- Interface documentation: See code repository README.md and source code comments
- Installation guide: Requires Windows 10/11, Python 3.8+, Android device with USB debugging enabled; dependent adb.exe and scrcpy.exe are already packaged in `dependencies/` directory
- Open Source License: Apache License 2.0