## Overview
Orchestrates the entire README generation process. It manages the step-by-step generation using prompts, handles context management between steps, and produces the final README document.

## Key Components

### ReadmeGenerator Class
```python
class ReadmeGenerator:
    def __init__(self, config: GeneratorConfig) -> None:
        self.config = config
        self.analyzer = RepositoryAnalyzer(self.config)
        self.llm = ChatOpenAI(model=config.model, temperature=0)
        self._has_checked_skipped = False
```

### Context Management
The generator maintains context between generation steps using a specialized prompt:
```python
self.context_prompt = PromptTemplate.from_template("""
    You are assisting in generating a README for a code repository.
    
    # Previous Outputs
    {previous_context}
    
    # Repository Analysis
    {repo_analysis}
    
    # Code Understanding
    {code_understanding}
    
    # Current Task
    {current_prompt}
""")
```

## Core Functionality

### 1. Step Management
```python
def extract_step_number(self, filename: Path | str) -> int:
    """Extract step number from filename."""
    try:
        if isinstance(filename, str):
            name = Path(filename).stem
        else:
            name = filename.stem

        # Look for a two-digit number at the start
        match = re.match(r"^(\d{2})-", name)
        if match:
            return int(match.group(1))
        return 0
    except (ValueError, TypeError, AttributeError):
        return 0
```

### 2. Step File Discovery
```python
def find_step_files(self) -> List[Path]:
    """Find all valid step files in the prompts directory."""
    # Get all potential step files
    step_files = [
        f for f in self.config.prompts_dir.glob("[0-9][0-9]-*.md")
        if self.extract_step_number(f) > 0
    ]

    # Filter out .SKIP files
    valid_files = [f for f in step_files if ".SKIP." not in f.name]

    # Sort by step number
    valid_files.sort(key=lambda f: self.extract_step_number(f))

    return valid_files
```

### 3. Context Preparation
```python
def prepare_context(self, current_step: int) -> str:
    """Prepare context by concatenating previous step outputs."""
    if current_step <= 1:
        return ""

    outputs = []
    for i in range(1, current_step):
        output_file = self.get_output_path(i)
        if output_file.exists() and output_file.stat().st_size > 0:
            outputs.append(output_file.read_text())

    return "\n\n".join(outputs)
```

## Generation Process

### 1. Main Execution Flow
```python
def run(self) -> None:
    """Main execution flow."""
    try:
        self.config.validate()
        os.chdir(self.config.target_repo)
        
        # Run analyzer
        analysis_result = self.analyzer.analyze_repository()
        
        # Check for existing README
        if "Non-empty README already exists" in analysis_result:
            logging.info(analysis_result)
            return
            
        # Process steps
        step_files = self.find_step_files()
        processed_any = False
        failed_steps = []
        
        for prompt_file in step_files:
            if not self.process_prompt(prompt_file):
                failed_steps.append(current_step)
            else:
                processed_any = True
                
        # Finalize README if any steps were processed
        if not self.config.only_mode and processed_any:
            self.finalize_readme()
```

### 2. Prompt Processing
```python
def process_prompt(self, prompt_file: Path) -> bool:
    """Process a single prompt file."""
    step_num = self.extract_step_number(prompt_file)
    output_file = self.get_output_path(step_num)
    
    # Get content from previous steps
    previous_context = self.prepare_context(step_num)
    
    # Get repository analysis
    repo_analysis = self.analyzer.analyze_repository(update=False)
    
    # Format prompt with enhanced code understanding
    formatted_prompt = self.context_prompt.format(
        previous_context=previous_context,
        repo_analysis=repo_analysis,
        code_understanding=code_understanding,
        current_prompt=prompt_content,
    )
    
    # Generate response using LLM
    response = self.llm.invoke(formatted_prompt)
    output_file.write_text(response.content)
```

### 3. README Finalization
```python
def finalize_readme(self) -> None:
    """Create the final README file."""
    # Find and sort output files
    existing_outputs = list(self.config.output_dir.glob("step_*_output.md"))
    existing_outputs.sort(key=lambda p: int(p.stem.split("_")[1]))
    
    # Combine outputs
    step_outputs = []
    for output_file in existing_outputs:
        content = output_file.read_text()
        step_outputs.append({
            "step": int(output_file.stem.split("_")[1]),
            "file": output_file.name,
            "content": content
        })
    
    # Generate final README
    final_prompt = PromptTemplate.from_template("""
        You are compiling the final README.md...
    """)
    
    response = self.llm.invoke(final_prompt.format(
        code_understanding=code_understanding,
        sections=formatted_sections
    ))
    
    # Write final README
    target_readme = self.config.target_repo / "ai.README.md"
    target_readme.write_text(response.content)
```
