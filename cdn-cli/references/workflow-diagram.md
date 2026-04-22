# Swagger Upgrade Workflow (Diagram)

End-to-end flow for upgrading a CLI extension (`cdn` or `front-door`) to a new swagger API version. See [aaz-dev-setup.md](./aaz-dev-setup.md) for the full step-by-step reference.

```mermaid
flowchart TD
    Start([User: upgrade swagger version]) --> Init{"Repos + venv<br/>ready?"}
    Init -- No --> Bootstrap["initialize_aaz_dev_env.ps1<br/>(clone 4 repos + azdev venv)"]
    Init -- Yes --> CheckRepos["check_repos.ps1<br/>(fast verify)"]
    Bootstrap --> Activate
    CheckRepos --> Activate["use_aaz_dev_env.ps1<br/>(activate venv + env vars)"]

    Activate --> Branch["git checkout -b branch<br/>(in extension + aaz)"]
    Branch --> Diff["swagger_diff.py<br/>--ext cdn|front-door<br/>--old X --new Y"]
    Diff --> Review1{{"User reviews diff,<br/>confirms to continue"}}

    Review1 --> WebUI["restart_aaz_dev.ps1<br/>(launch http://127.0.0.1:5000)"]
    WebUI --> AutoSelect["auto_select_resources.py<br/>--ext cdn|front-door --version Y<br/>(create workspace)"]

    AutoSelect --> Export{{"Manual:<br/>user clicks Export in Web UI<br/>(or --workspace auto-exports)"}}
    Export --> Generate["generate_cli.py<br/>--ext cdn|front-door --version Y<br/>(bump versions + PUT -> generate)"]

    Generate --> Review2{{"User reviews<br/>git diff"}}
    Review2 --> Test["azdev test / azdev linter"]
    Test -- Fail --> Fix[Fix] --> Test
    Test -- Pass --> Bump["update_history.py<br/>--ext cdn|front-door<br/>--version X.Y.Z --swagger-version Y"]

    Bump --> Commit[["git add + commit<br/>(in extension + aaz)"]]
    Commit --> End([Done])

    classDef script fill:#d4edda,stroke:#28a745,color:#000;
    classDef manual fill:#fff3cd,stroke:#ffc107,color:#000;
    classDef decision fill:#cfe2ff,stroke:#0d6efd,color:#000;
    class Bootstrap,CheckRepos,Activate,Diff,WebUI,AutoSelect,Generate,Bump script;
    class Review1,Review2,Export manual;
    class Init decision;
```

## Legend

- **Green** — scripted step (invoke the named file under `.github/cdn-cli/scripts/`)
- **Yellow** — requires human action (review diff, click Export in the Web UI)
- **Blue** — conditional branch

## Script Index

| Script | Purpose |
|---|---|
| [initialize_aaz_dev_env.ps1](../scripts/initialize_aaz_dev_env.ps1) | One-time bootstrap: clone 4 repos + create azdev venv |
| [check_repos.ps1](../scripts/check_repos.ps1) | Lightweight verify that 4 repos exist (no clone) |
| [use_aaz_dev_env.ps1](../scripts/use_aaz_dev_env.ps1) | Activate venv + export env vars in a new terminal |
| [restart_aaz_dev.ps1](../scripts/restart_aaz_dev.ps1) | Launch / relaunch aaz-dev Web UI on port 5000 |
| [swagger_diff.py](../scripts/swagger_diff.py) | Compare two swagger API versions |
| [auto_select_resources.py](../scripts/auto_select_resources.py) | Create workspace with resources auto-selected |
| [generate_cli.py](../scripts/generate_cli.py) | Bump command versions + PUT to trigger CLI code gen |
| [update_history.py](../scripts/update_history.py) | Bump `setup.py` VERSION + prepend `HISTORY.rst` entry |
