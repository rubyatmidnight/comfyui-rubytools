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

### Video:
#### PyAV-backed frame extraction, with NVDEC hardware decode when the GPU and codec allow it. Requires `av` (`pip install av`).
- Video Frame Extract  
  Decode a video into an IMAGE batch, keeping every Nth frame, optionally saving to disk as it goes.

- Video Frames To Disk  
  Bulk-extract one video or a whole folder straight to PNG/JPG/WEBP with a threaded writer pool.

- Video Endpoint Frames  
  Grab the first and last frame of a video.

### Audio:
#### Homebrew Kokoro TTS on the local ONNX model. Requires `kokoro-onnx` (`pip install kokoro-onnx`) plus the model files.
- Kokoro TTS (local)  
  Speak text with any installed Kokoro voice, with optional two-voice blending. Outputs ComfyUI AUDIO.

- Kokoro Voice List  
  List the voices found in the installed voices file, filtered by prefix.

### Pager:
#### Paper notes to a thermal printer. The node writes into an inbox folder; a small daemon prints whatever lands there.
- Pager: Send Page  
  Queue a text note and/or an image for the pager daemon, optionally waiting until it prints.

### Frontend:
- Auto Bookmarks  
  Pre-selects the "Bookmarked" chip whenever the node search popover opens, so typed searches are scoped to
  your bookmarks until you deselect it. Needs at least one bookmarked node. Shows up under Settings > Extensions
  as `rubytools.autobookmarks`.

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

### Video Frame Notes

All three nodes use PyAV. Install it into ComfyUI's python with `pip install av`; the rest of the
pack keeps working without it, the video nodes just raise a clear error when they run.

Hardware decode: `use_hwaccel` tries NVDEC for `h264`/`hevc` and silently falls back to CPU decode
when CUDA, the codec, or the PyAV build can't do it. The console line for each video prints
`HW: NVDEC` or `HW: CPU` so you can tell which path ran.

Paths: `video_path` / `source_path` accept an absolute path, or a relative one resolved against
ComfyUI's `input` folder. Output folders are relative to ComfyUI's `output` folder unless absolute.
`randomize_subfolder` reproduces the original script's behaviour, a random hex subfolder whose name
also prefixes every frame file; turn it off to use the video's own name instead.

- `Video Frame Extract`: returns an IMAGE batch plus `frame_count`, `fps`, and the save folder.
- `Video Frame Extract`: `step` keeps every Nth frame (`30` is about one per second on 30fps footage),
  `start_frame` skips ahead, `max_frames` caps the batch. The whole batch is held in RAM, so
  `max_frames` defaults to 64; set it to 0 only when you know the video is short.
- `Video Frame Extract`: frames must all be the same size to form one batch; variable-resolution
  files raise an error and should go through `Video Frames To Disk` instead.
- `Video Frames To Disk`: point `source_path` at a file or a folder; `extensions` filters folder scans
  and `parallel_videos` decodes several videos at once. Returns a per-file summary and the total count.
- `Video Frames To Disk`: `skip_existing` leaves frames already on disk alone, so an interrupted run
  can be resumed (keep `randomize_subfolder` off for that, otherwise each run gets a new folder).
- `Video Endpoint Frames`: always outputs both endpoints; `save_which` only controls what gets written.
  The last frame comes from a seek to the end, with a full-decode fallback for short or odd files.
- All three respect ComfyUI's progress bar and cancel button, and re-run when the source file changes
  on disk even if the widget values are identical.

### Kokoro TTS Notes
- Model files come from the kokoro-onnx releases: `kokoro-v1.0.onnx` and `voices-v1.0.bin`. The node looks for
  them in, in order: the `model_dir` input, the `KOKORO_MODEL_DIR` environment variable, `model_dir` in
  `nodes/kokoro.json` (copy `kokoro.example.json`), then `ComfyUI/models/kokoro/`.
- `provider` picks the ONNX Runtime backend. `auto` prefers CUDA, then DirectML, then CPU, depending on which
  onnxruntime build is installed. CPU is fine for short clips: a sentence takes a few seconds.
  For CUDA, install `onnxruntime-gpu` in place of `onnxruntime` (matching your CUDA major version). The node
  preloads cuDNN from torch's own lib folder, so no separate cuDNN install is needed when torch is CUDA-enabled.
  On a GPU a sentence takes a fraction of a second after the one-time model load.
- The voice dropdown is read from the voices file, so it matches what is installed. `blend_voice` mixes a second
  voice's style vector into the first; `blend_amount` 0 is all first voice, 1 is all blend voice.
- `text_is_phonemes` skips espeak and feeds IPA straight to the model. `sentence_pause` and `clause_pause`
  are the silences inserted at sentence ends and at commas.
- Output is 24 kHz mono AUDIO, so it connects directly to the core Save Audio and Preview Audio nodes.
  The model stays loaded between runs; switching provider or model folder reloads it.

### Pager Notes
- The node only writes files. Anything that watches the inbox folder and prints what shows up completes the
  loop. `examples/pager/pager_daemon_example.py` is a working sample daemon: set `PRINT_COMMAND` to whatever
  prints a PNG on your printer (a vendor CLI, `lp`, an ESC/POS script) and run it next to the inbox.
- Inbox location, in order: the `inbox_path` input, the `RUBY_PAGER_INBOX` environment variable, then `inbox`
  in `nodes/pager.json` (copy `pager.example.json`). `log` in the same file points at the daemon's `pager.jsonl`
  when it is not next to the inbox.
- Text pages are written as `From:` / `Icon:` headers, a blank line, then the body. Images are scaled to
  384 px wide (a 57 mm strip), converted to 1-bit with optional dithering, and queued as their own page.
- `always_send` is on by default so the page goes out on every run; turn it off to let ComfyUI's cache skip
  re-sending unchanged inputs.
- `wait_for_print` tails the daemon log and reports `printed`, `print_failed`, `render_failed` or `timeout`
  per file. Files are timestamped with a short random tag so pages sent in the same second never collide.

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
### v0.9.1
Added video frame extraction nodes (PyAV + optional NVDEC)
### v0.9.2
Added Kokoro TTS (local ONNX) nodes and the Pager node with a sample inbox daemon
