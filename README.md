# RubyTools - Ruby's Custom Nodes for ComfyUI

These are a handful of custom nodes, some of which are my own conception a couple of which are adapted from other repos, though re-written in my own format or needs profiling. Any nodes which are primarily ideated from another custom node source are have been cited and mentioned by the respective node.

Mostly, these fill in a few gaps in functionality that I feel are important enough to create a custom solution. Anything in here I've needed to use more than once, or had potentially made some complicated math expression monster before deciding to do it this way. 

If you want the nanoruby (NanoGPT nodes) then you can find them in their own repo once I publish them; they are taking longer. 

### Utilities:
- Hash: HMAC tool  
  Use inputs to perform an HMAC hash on a message with a key.

- Hash: SHA-256  
  Hash a string with SHA-256.

- Image Hash  
  Hash an image with SHA-256 and cache it.

- Auto Tag Formatting  
  Format tag index text entries for workflows like Hydrus.

- Embed Image Tags + Index  
  Embed tags into PNG/JPG metadata and append a filename+tags line to a master text index.

- Filename Save Aide  
  Create a consistent date-based nested folder structure.

- Regex Switch  
  Select an output based on a regex pattern match.

- Denoise/Seed Iterator  
  Iterate denoise values between a floor and 1.0, then increment seed.

- Preset Text  
  Load presets from JSON instead of editing long in-app text fields.

- Preset Text Multi  
  Combine multiple presets with a separator.

- Sequential Image Load From Folder (no batching)  
  Load one image per run and increment an index.

- GPT Token Count  
  Count prompt tokens in OpenAI-style token space.

- CLIP Chunk Estimate  
  Estimate CLIP prompt token chunks and capacity.

- Math Expression  
  Evaluate safe custom math expressions with named inputs.

### String/Json Utilities:
- Integer to String: `1 -> "1"`
- Float to String: `0.5 -> "0.5"`
- String to Int: `"1" -> 1`
- String to Float: `"0.5" -> 0.5`
- Boolean to String: `True -> "true"` / `False -> "false"`
- Hex to Integer: `"0x1A" -> 26`
- Integer to Hex: `26 -> "0x1A"`
- Bypass Switch: bypass a node output using a boolean toggle.
- String Concatenate (3, 4, 6): combine multiple string inputs.
- Mixed Int/Str Concatenate (4): concatenate mixed numeric and string inputs.
- Iterate Float: simple float floor/ceiling iterator.
- Iterate Int: simple integer iterator.
- Extract JSON Field: return a field from JSON as plain text.
- Format JSON Utility: format JSON text for readability and file appends.

### RPG-Related:
#### These are random RPG-related nodes that I was trying to make for a procedural comfyui-constrained RPG engine.  
- Character Card
- Context Card
- Session Memory (RP)
- Memory Store (RP)
- Memory Init (RP)

### Memory Related:
#### I was using text files to store memory addresses for some complicated node chains, and wanted to skip the middle man. 
- Simple Memory
- Simple File
- Text Load
- Text Save
- Text Show




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

### GPT Token Count

Counts text in OpenAI-style token space.

- Uses `tiktoken` when installed.
- Falls back to local estimate if `tiktoken` is unavailable.
- Accepts either model names (for example `gpt-4o-mini`) or encoding names (for example `o200k_base`, `cl100k_base`).

Options:
- `model_or_encoding`: tokenizer source used for counting.
- `context_window`: used to compute `%` usage and over-limit flag.

Returns:
- `tokens`, `context_window`, `percent_used`, `over_limit`, `method`.

### Math Expression

Evaluates a safe math expression without using raw `eval`.

- Uses named inputs `a` through `f`.
- Supports operators like `+`, `-`, `*`, `/`, `//`, `%`, `**`, and parentheses.
- Supports comparisons like `>`, `<`, `>=`, `<=`, `==`, `!=`.
- Includes constants `pi`, `math_e`, `tau`.
- Includes helpers like `abs`, `min`, `max`, `round`, `floor`, `ceil`, `sqrt`, `log`, `sin`, `cos`, `tan`, `clamp`, `lerp`, `invlerp`, `remap`, `wrap`, `pingpong`, and `ifelse`.
- Includes random helpers `rand()` / `rand(min, max)` and `randint(min, max)`.
- Also supports inline conditional expressions like `a if b > 0 else c`.

Options:
- `expression`: formula text using `a`-`f`.
- `a`-`f`: numeric input values for the expression.

Returns:
- `value`, `int_value`, `text`, `ok`.

### CLIP Chunk Estimate

Estimates CLIP prompt chunk usage for Comfy-style prompt chunking.

- Uses a local heuristic estimator.
- Default payload size is `75` tokens per chunk.
- Useful for translated prompts or long weighted prompt strings.

Options:
- `payload_tokens_per_chunk`: payload capacity per chunk.

Returns:
- `estimated_tokens`, `chunks`, `tokens_with_special`, `total_payload_capacity`, `fits_single_chunk`, `method`.

### String / JSON Utility Notes

- `String Concatenate (3/4/6)`: joins non-empty inputs with `separator`.
- `Mixed Concatenate (4)`: accepts strings/ints/floats and formats float precision with `float_decimals`.
- `String to Integer` / `String to Float`: parse with fallback `default` on invalid input.
- `Extract JSON Field`: supports dot-path lookup (for example `choices.0.message.content`).
- `Format JSON Utility`: creates a readable block for logs/files, optional token line.
- `Bypass Switch`: routes `bypass_value` when `bypass=true`, otherwise `active_value`.

### Token Utility Notes

- `GPT Token Count`: OpenAI-style tokenizer count with `% context used` and limit check.
- `GPT Token Count`: accepts model or encoding input (`gpt-4o-mini`, `cl100k_base`, `o200k_base`, etc).
- `CLIP Chunk Estimate`: estimates token load and chunk count for CLIP prompt windows.
- `CLIP Chunk Estimate`: reports chunk payload capacity and single-chunk fit.

### Math Utility Notes

- `Math Expression`: safe formula evaluator for small workflow calculations.
- `Math Expression`: returns float, int, string, and success flag outputs.
- `Math Expression`: uses fixed named inputs instead of exposing arbitrary code execution.
- `Math Expression`: recalculates on each run when the expression uses `rand()` or `randint()`.

### File / IO Utility Notes

- `Text Load` / `Text Save`: reads or writes text in Comfy `input`/`output` with optional subfolder and encoding.
- `Text Save`: `append` adds to file, `ensure_newline` makes one trailing newline.
- `Sequential Image From Folder`: lists files by pattern and returns one image per run.
- `Sequential Image From Folder`: `auto_increment` advances index, `reset` returns to `start_index`, `loop` wraps on overflow.
- `Auto Tag Concat`: writes lines in `[filename={tags}]` format for tag indexing.
- `Embed Image Tags + Index`: minimal inputs (`image`, `image_path`, `tags`, `metadata_key`, `index_filepath`).
- `Embed Image Tags + Index`: supports `.png`, `.jpg`, `.jpeg`; appends `filename<TAB>tags` into `output/<index_filepath>`.

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