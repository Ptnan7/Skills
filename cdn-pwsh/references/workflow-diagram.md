# AutoRest Module Maintenance Workflow (Diagram)

End-to-end flow for updating a CDN/AFD AutoRest-generated PowerShell module (`Cdn`, `FrontDoor`, etc.). See [autorest-generation.md](./autorest-generation.md) and [development.md](./development.md) for the full step-by-step reference.

```mermaid
flowchart TD
    Start([User: update PowerShell module]) --> Init{"pwsh + swagger<br/>cloned?"}
    Init -- No --> Bootstrap["initialize_pwsh_env.ps1<br/>(clone pwsh + swagger)"]
    Init -- Yes --> Activate
    Bootstrap --> Activate["use_pwsh_env.ps1<br/>(set PWSH_REPO_PATH +<br/>AAZ_SWAGGER_PATH)"]

    Activate --> Diff["swagger_diff.py<br/>--ext cdn --old X --new Y<br/>(shared with cdn-cli)"]
    Diff --> Review1{{"User reviews diff"}}

    Review1 --> UpdateReadme{{"Manual + Copilot:<br/>edit .Autorest/README.md<br/>(commit hash, API version,<br/>directives)"}}
    UpdateReadme --> Approve1{{"User approves"}}

    Approve1 --> AutoRest[["autorest<br/>(from .Autorest/)"]]
    AutoRest -- Fail --> FixGen["Minimal fix<br/>(scoped to src/&lt;Module&gt;/)"]
    FixGen --> AutoRest
    AutoRest -- Success --> ReviewCustom{{"Review custom/<br/>for swagger impact"}}

    ReviewCustom --> Build[["pwsh -File ./build-module.ps1"]]
    Build -- Fail --> FixBuild[Fix] --> Build
    Build -- Success --> Analyze["analyze_module.ps1<br/>-Module Cdn|FrontDoor<br/>(new/removed cmdlets +<br/>unfilled example placeholders)"]

    Analyze --> NewTests{{"Manual + Copilot:<br/>write Pester tests for new cmdlets +<br/>fill example placeholders"}}
    NewTests --> AskTest{{"Run tests?"}}
    AskTest -- Yes --> RunTest[["test-module.ps1 -Record"]]
    AskTest -- No --> AskCommit
    RunTest -- Fail --> FixTest[Fix] --> RunTest
    RunTest -- Pass --> AskCommit{{"Commit?"}}

    AskCommit -- Yes --> Commit[["git add src/&lt;Module&gt;/<br/>git commit"]]
    AskCommit -- No --> End
    Commit --> End([Done])

    classDef script fill:#d4edda,stroke:#28a745,color:#000;
    classDef manual fill:#fff3cd,stroke:#ffc107,color:#000;
    classDef decision fill:#cfe2ff,stroke:#0d6efd,color:#000;
    classDef tool fill:#e2e3e5,stroke:#6c757d,color:#000;
    class Bootstrap,Activate,Diff,Analyze script;
    class Review1,UpdateReadme,Approve1,ReviewCustom,NewTests,AskTest,AskCommit manual;
    class AutoRest,Build,RunTest,Commit tool;
    class Init decision;
```

## Legend

- **Green** — scripted step (invoke the named file under `.github/cdn-pwsh/scripts/`)
- **Grey** — external tool (autorest / build-module / test-module / git)
- **Yellow** — requires user decision or action
- **Blue** — conditional branch

## Script Index

| Script | Purpose |
|---|---|
| [initialize_pwsh_env.ps1](../scripts/initialize_pwsh_env.ps1) | One-time bootstrap: clone `azure-powershell` + `azure-rest-api-specs` |
| [use_pwsh_env.ps1](../scripts/use_pwsh_env.ps1) | Export `PWSH_REPO_PATH` + `AAZ_SWAGGER_PATH` in a new terminal |
| [analyze_module.ps1](../scripts/analyze_module.ps1) | Report new/removed cmdlets + unfilled example placeholders |

The swagger diff script lives in the sibling skill: [`.github/cdn-cli/scripts/swagger_diff.py`](../../cdn-cli/scripts/swagger_diff.py).
