## System Overview

A code that automatically generates comprehensive README documentation for code repositories. It combines repository analysis, code understanding, and AI-powered content generation to create detailed, contextually aware documentation.

## Core Components

```mermaid
    A[main.py] --> B[config.py]
    A --> C[readme_generator.py]
    C --> D[analyzer.py]
    D --> E[code_understanding_analyzer.py]
    C --> F[LLM Service]
    D --> F
    E --> F
```

### Component Responsibilities

1. **main.py**
   - Entry point for the application
   - CLI argument parsing
   - High-level error handling
   - Process orchestration

2. **config.py**
   - Configuration management
   - Path resolution and validation
   - Environment setup
   - Directory structure management

3. **readme_generator.py**
   - Generation process orchestration
   - Step-based prompt processing
   - Context management between steps
   - Final README compilation

4. **analyzer.py**
   - Repository structure analysis
   - Language detection
   - Dependency identification
   - Build system detection
   - Custom tool recognition

5. **code_understanding_analyzer.py**
   - Deep code analysis
   - AST parsing for Python
   - Pattern matching for other languages
   - Component relationship mapping
   - Code structure understanding

## Data Flow

```mermaid
    participant CLI as main.py
    participant Config as config.py
    participant Generator as readme_generator.py
    participant Analyzer as analyzer.py
    participant CodeAnalyzer as code_understanding_analyzer.py
    participant LLM as LLM Service

    CLI->>Config: Initialize configuration
    Config-->>CLI: Validated config
    CLI->>Generator: Start generation
    Generator->>Analyzer: Request repository analysis
    Analyzer->>CodeAnalyzer: Request code analysis
    CodeAnalyzer->>LLM: Send code understanding prompt
    LLM-->>CodeAnalyzer: Code understanding response
    CodeAnalyzer-->>Analyzer: Code analysis results
    Analyzer-->>Generator: Repository analysis
    Generator->>LLM: Send generation prompts
    LLM-->>Generator: Generated content
    Generator->>Generator: Compile final README
```

## Key Processes

### 1. Repository Analysis Process

```mermaid
    A[Start Analysis] --> B[Scan Repository]
    B --> C[Identify Key Files]
    B --> D[Detect Languages]
    C --> E[Parse Config Files]
    D --> F[Find Entry Points]
    E --> G[Extract Dependencies]
    F --> H[Build System Detection]
    G --> I[Generate Analysis Report]
    H --> I
```

### 2. Generation Process

```mermaid
    A[Load Prompts] --> B[Process Step 1]
    B --> C[Process Step 2]
    C --> D[Process Step N]
    D --> E[Compile Results]
    E --> F[Generate Final README]
    F --> G[Cleanup Steps]
```