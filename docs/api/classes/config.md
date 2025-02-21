## Overview
`config.py` the configuration management system for the README generator.

## Key Components

### GeneratorConfig Class
```python
@dataclass
class GeneratorConfig:
    target_repo: str
    prompt_collection: str = "default"
    start_step: Optional[int] = None
    only_mode: bool = False
    model: str = "gpt-4o"
    keep_steps: bool = False
```

#### Required Parameters
- `target_repo`: Path to the repository to analyze

#### Optional Parameters
| Parameter | Default | Description |
|-----------|---------|-------------|
| `prompt_collection` | "default" | Name of the prompt collection to use |
| `start_step` | None | Step number to start from |
| `only_mode` | False | Run only a specific step |
| `model` | "gpt-4o" | OpenAI model identifier |
| `keep_steps` | False | Preserve intermediate step files |

### Path Resolution
The class resolves and manages several important paths:
```python
def __post_init__(self) -> None:
    self.target_repo = Path(self.target_repo).resolve()
    self.script_dir = Path(__file__).parent.resolve()
    self.prompts_dir = self.script_dir / "prompts" / self.prompt_collection
    self.output_dir = self.target_repo / "output"
```

#### Key Paths
- `target_repo`: Absolute path to the target repository
- `script_dir`: Directory containing the generator scripts
- `prompts_dir`: Directory containing prompt templates
- `output_dir`: Directory for generation outputs

## Integration Points

### With main.py
- Receives configuration from command-line arguments
- Example:
  ```python
  config = GeneratorConfig(
      target_repo=args.repo,
      prompt_collection=args.collection,
      start_step=args.step,
      only_mode=args.only,
      model=args.model,
      keep_steps=args.keep_steps,
  )
  ```

### With readme_generator.py
- Provides configuration for the generation process
- Manages paths for prompt files and outputs
- Controls step execution behavior

### With analyzer.py
- Provides repository path for analysis
- Determines output locations for analysis results

### Configuration Usage
1. Always validate configuration after creation:
   ```python
   config = GeneratorConfig(...)
   config.validate()
   ```

2. Use resolved paths:
   ```python
   absolute_path = config.target_repo / "some_file"
   ```

3. Check path existence before operations:
   ```python
   if config.prompts_dir.is_dir():
       # Safe to proceed
   ```

### Error Messages
The configuration system provides detailed error messages:
```python
"Target repository directory does not exist: /path/to/repo"
"Prompt collection 'custom' not found. Available: default, minimal, full"
```

## Testing and Validation
When testing configurations:
1. Verify path resolution
2. Check directory existence
3. Validate prompt collection availability
4. Ensure output directory permissions

## Related Files
- `main.py`: Creates configuration from CLI arguments
- `readme_generator.py`: Uses configuration for generation process
- `analyzer.py`: Uses configuration for repository analysis

## Debugging Tips
1. Print resolved paths for verification:
   ```python
   print(f"Target repo: {config.target_repo}")
   print(f"Prompts dir: {config.prompts_dir}")
   ```

2. Check directory existence:
   ```python
   print(f"Target exists: {config.target_repo.is_dir()}")
   print(f"Prompts exist: {config.prompts_dir.is_dir()}")
   ```

3. List available prompt collections:
   ```python
   collections = [p.name for p in (config.script_dir / "prompts").iterdir() if p.is_dir()]
   print(f"Available collections: {collections}")
   ```