# Developer Tasks

- Running mypy in a pre-commit hook is a total mess to set-up. Therefore, regularly run mypy manually:
```
mypy .
```

- Commented-out code artefacts have been excluded from the codechecker rules. Every now and then, clean up manually:
```
ruff check --select "ERA001" .
```

- Regularly update dependencies:
- ```
# update third-party dependencies
poetry update

# update pre-commit hooks
pre-commit autoupdate
```
