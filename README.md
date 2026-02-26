# RubyTools - Ruby's Custom Nodes for ComfyUI

These are a handful of custom nodes, some of which are my own conception a couple of which are adapted from other repos, though re-written in my own format or needs profiling. Any nodes which are primarily ideated from another custom node source are have been cited and mentioned by the respective node.

Mostly, these fill in a few gaps in functionality that I feel are important enough to create a custom solution. Anything in here I've needed to use more than once, or had potentially made some complicated math expression monster before deciding to do it this way. 

If you want the nanoruby (NanoGPT nodes) then you can find them in their own repo once I publish them; they are taking longer. 

### Utilities:
Hash: HMAC tool,
(Use inputs to perform an HMAC function hash on a message with a key)
Hash: SHA-256
(Hash a string with SHA-256)
Image Hash
(Hash an image using SHA-256, and cache it for later use)
Auto Tag Formatting
(Formatting for creating tag index text files when tagging for e.g. hydrus)
Filename Save Aide
(Creates a consistent nested folder structure based on the date for quick save file formatting)
Regex Switch
(Select an output based on a regex pattern match)
Denoise/Seed Iterator
(Iterates through denoise values between a floor and 1.0, then increments seed. Optionally uses a fixed denoise value and iterates seed every step instead. Supports auto-increment mode for self-contained iteration. For testing denoise values across thresholds without needing to stop an infinite generation loop, as it will pick a new seed and keep trying another cycle.)
Preset Text
(Create presets in a json instead of weird in-app text fields that are hard to edit programatically. Based on pyyyys' preset node, but done totally differently with an external json source file and better organization of presets.)
Preset Text Multi
(Combine multiple presets with a separator, same source as Preset Text)
Sequential Image Load From Folder (no batching)
(Loads images from a folder one at a time, and increments a counter for each image loaded, useful for tagging image sets without needing to re-size or batch images, and indexes all of them so you can compare the tag index to the image index.)

### String/Json Utilities:
Integer to String,
1 -> "1"
Float to String,
0.5 -> "0.5"
String to Int,
"1" -> 1
String to Float,
"0.5" -> 0.5
Boolean to String,
True -> "true"
False -> "false"
Hex to Integer,
"0x1A" -> 26
Integer to Hex
26 -> "0x1A"
Bypass Switch
(Bypass a node's output based on a boolean input), (based on the rgthree node set with similar naming)
String Concatenate (3, 4, 6)
(Need to concatenate more than 2 strings and tired of wiring together fifty concatenates? Then this is for you.)
Mixed Int/Str Concatenate (4),
(Need to mix in integers? Then this will work for that but not for certain other things)
Iterate Float,
(Similar to the denoise iterator, but is a simple floor + ceiling iteration for just a float of whatever)
Iterate Int,
(Same but for integers)
Extract JSON Field,
(Extract a field from a json string and return it as a non-json string. Used for LLM responses)
Format JSON Utility,
(Format a json string for easy reading and appending to a file)

### RPG-Related:
#### These are random RPG-related nodes that I was trying to make for a procedural comfyui-constrained RPG engine.  
Character Card,
Context Card,
Session Memory (RP),
Memory Store (RP),
Memory Init (RP)

### Memory Related:
#### I was using text files to store memory addresses for some complicated node chains, and wanted to skip the middle man. 
Simple Memory,
Simple File,
Text Load,
Text Save, 
Text Show,




## Installation

### Manual Installation
1. Navigate to your ComfyUI custom nodes directory:
   ```bash
   cd ComfyUI/custom_nodes
   ```

2. Clone this repository:
   ```bash
   git clone https://github.com/rubyatmidnight/comfyui-rubytools
   ```

3. Restart ComfyUI

## Detailed Node Descriptions

### Random String From List

Picks one line from `lines_text` using the selected mode.

- `random_secure`: chooses an index with Python `secrets` (`randbelow`), which uses cryptographically secure OS randomness; picks are independent and may repeat.
- `shuffle_no_repeat`: builds a shuffled index order and returns each entry once before reshuffling.
- `round_robin`: deterministic cycling in source order (`0,1,2...` then wrap).
- `even_index` / `odd_index`: chooses randomly from only even or odd line indices.
- `first` / `last`: always returns index `0` or the final index.

Options:
- `slot`: shared state key for round-robin and shuffle tracking.
- `reset`: clears that slot's counter and shuffle state.
- `strip_empty`: trims lines and removes blanks before picking.

### String / JSON Utility Notes

- `String Concatenate (3/4/6)`: joins non-empty inputs with `separator`.
- `Mixed Concatenate (4)`: accepts strings/ints/floats and formats float precision with `float_decimals`.
- `String to Integer` / `String to Float`: parse with fallback `default` on invalid input.
- `Extract JSON Field`: supports dot-path lookup (for example `choices.0.message.content`).
- `Format JSON Utility`: creates a readable block for logs/files, optional token line.
- `Bypass Switch`: routes `bypass_value` when `bypass=true`, otherwise `active_value`.

### File / IO Utility Notes

- `Text Load` / `Text Save`: reads or writes text in Comfy `input`/`output` with optional subfolder and encoding.
- `Text Save`: `append` adds to file, `ensure_newline` makes one trailing newline.
- `Sequential Image From Folder`: lists files by pattern and returns one image per run.
- `Sequential Image From Folder`: `auto_increment` advances index, `reset` returns to `start_index`, `loop` wraps on overflow.
- `Auto Tag Concat`: writes lines in `[filename={tags}]` format for tag indexing.

### Crypto / Hash Utility Notes

- `Hash: SHA-256`: returns both hex and base64 digest from input text.
- `Hash: HMAC`: signs `message` with `key` using selected algorithm (`sha256`, `sha512`, `sha1`, `md5`).
- `Image Hash Cache`: emits image plus deterministic SHA-256 hash for cache/invalidation workflows.

### Preset Utilities

- `Preset Text`: loads one entry from `nodes/presets.json` using `category/name`.
- `Preset Multi Text (4)`: combines up to four preset entries with a custom separator.

### RPG / Memory Notes

- `Character Card` / `Context Card`: build formatted text files from multiline bullet-style inputs.
- `Session Memory (RP)`: file-backed read/write/append scoped by `session_id`.
- `Memory Store (RP)`: JSON key-value store with get/set/append/delete/list operations.
- `Memory Init (RP)`: creates or reuses a session folder path.
- `Simple Memory`: namespace-based persistent key-value JSON store.
- `Simple File`: lightweight text file read/write/append in output subfolders.

## Changelog

### v0.5.0
initial release
### v0.5.1
combined sets
### v0.9.0
Split nanoruby into a nanogpt repo and a rubytools repo. This is rubytools