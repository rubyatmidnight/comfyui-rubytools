# RubyTools - Ruby's Custom Nodes for ComfyUI

These are a handful of custom nodes, some of which are my own conception and others are convenieced from other repos, though re-written in my own format. Any nodes which are primarily ideated from another custom node source are have been cited and will be linked in this readme. 

Mostly, these fill in a few gaps in functionality that I feel are important enough to create a custom solution. Anything in here I've needed to use more than once, or had potentially made some complicated math expression monster before deciding to do it this way.

Nodes Included:

### Utilities:
Hash: HMAC tool,
Hash: SHA-256,
Image Hash,
Auto Tag Formatting,
Filename Save Aide
Regex Switch,
Denoise/Seed Iterator,
Preset Text,
Preset Text Multi,
Sequential Image Load From Folder (no batching),

### String/Json Utilities:
Integer to String,
Float to String,
String to Int,
String to Float,
Boolean to String,
Hex to Integer,
Integer to Hex,
Bypass Switch,
String Concatenate (3, 4, 6),
Mixed Int/Str Concatenate (4),
Iterate Float,
Iterate Int,
Extract JSON Field,
Format JSON Utility,


### RPG-Related:
Character Card,
Context Card,
Session Memory (RP),
Memory Store (RP),
Memory Init (RP)

### Memory Related:
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
   git clone https://github.com/rubyatmidnight/comfyui-nanoruby
   ```

3. Restart ComfyUI

## Nodes

### Denoise + Seed Iterator
**Category**: `Ruby's Nodes/sampling`

Automates seed and denoise iteration for testing ranges of denoise values across similar input parameters, e.g., to test every 0.04 of a denoise set. Previously I was using mutliple math expression nodes to accomplish this task. This simplifies the issue. 

#### Features
- **Variable Denoise Mode**: Cycles through N evenly-spaced denoise values between a floor and 1.0, incrementing seed after each complete cycle. It will automatically determine how far it needs to go each step. 
- **Fixed Denoise Mode**: Basically, to turn it off.
- **Configurable**: Set denoise floor, number of steps, and toggle between modes. 

#### Inputs
- `iteration` (INT): Current iteration index, typically from a loop counter
- `base_seed` (INT): Starting seed value
- `denoise_steps` (INT): Number of denoise values to cycle through before incrementing seed
- `denoise_floor` (FLOAT): Minimum denoise value (max is always 1.0)
- `use_fixed_denoise` (BOOLEAN): Toggle between fixed and variable denoise modes
- `fixed_denoise` (FLOAT): Fixed denoise value (only used when toggle is True)

#### Outputs
- `seed` (INT): Calculated seed for current iteration
- `denoise` (FLOAT): Calculated denoise for current iteration

#### Example Usage

**Variable Denoise Mode** (`use_fixed_denoise = False`):
- Settings: `denoise_floor=0.6`, `denoise_steps=5`, `base_seed=42`
- Iteration 0-4: denoise cycles 0.6 → 0.7 → 0.8 → 0.9 → 1.0, seed stays at 42
- Iteration 5-9: denoise cycles 0.6 → 0.7 → 0.8 → 0.9 → 1.0, seed increments to 43
- And so on...

**Fixed Denoise Mode** (`use_fixed_denoise = True`):
- Settings: `fixed_denoise=0.8`, `base_seed=42`
- Every iteration increments seed: 42, 43, 44, 45...
- Denoise remains constant at 0.8

#### Algorithm Details

**Variable Denoise**:
```python
seed = base_seed + (iteration // denoise_steps)
denoise = denoise_floor + ((iteration % denoise_steps) * ((1 - denoise_floor) / denoise_steps))
```

**Fixed Denoise**:
```python
seed = base_seed + iteration
denoise = fixed_denoise
```

## Contributing

If there are any serious fatal flaws, create an issue in the repo, otherwise this is mostly for myself. The nano-gpt nodes are likely the most likely to have errors. 

## License

MIT License - See LICENSE file for details

## Author

Rubyatmidnight

## Changelog

### v0.5.0
initial release
### v0.5.1
combined sets