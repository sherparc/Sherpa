# ADR-0044 — CI definitions are found by directory where the platform fixes no file name

**Status:** accepted · **Date:** 2026-09-17 · **Deciders:** Andrei

## Context

`conventions.ci` names the CI definitions of a repository so the harness can point an agent at them. The
detector matched file names only: `.github/workflows/*`, `.gitlab-ci.yml`, `azure-pipelines*.yml`,
`Jenkinsfile`, `.circleci/config.yml`, `bitbucket-pipelines.yml`, `.drone.yml`. GitHub, GitLab, CircleCI and
Bitbucket fix the name, so that worked. Azure DevOps does not: a pipeline is registered in the service with a
path to any YAML file, and `azure-pipelines.yml` is only the name the wizard proposes. Real .NET monorepos keep
a dozen pipelines under `pipelines/` with names like `build_artifacts.yml`, `backend_integration.yml`,
`frontend_integration.yml`; a 15k-file repository scanned this way reported `ci: []` next to twenty container
files.

## Decision

1. A YAML file under a directory named `pipelines`, `.pipelines`, `.azure-pipelines` or `.azuredevops` — at
   any depth, `.yml` or `.yaml` — is a CI definition. The match stays on the path, no file content is read:
   the scanner reads blobs only for manifests, and a directory called `pipelines` holding YAML is CI in
   practice; a data-pipeline YAML there would be the exception that a `sherpa.toml` override can cover later.
2. `azure-pipelines*.yaml` joins `azure-pipelines*.yml`. Scripts next to the pipelines (`pipelines/scripts/*.ps1`)
   are not CI definitions.
3. The model schema description and `docs/concepts/scan.md` name the directories; the detector's patterns stay
   the single list in `scan/t1_modules.py`.

## Consequences

- A repository that keeps Azure pipelines under `pipelines/` gets its CI files in the model and in the owner
  docs; the model of a repository without such a directory does not change.
- Container files keep their precedence rule: a file is CI first, container second, so
  `tests/docker-compose-scenario.yml` stays a container file and `pipelines/x.yml` never becomes one.
- Content-based detection (top-level `pool`, `stages`, `trigger`) stays out until a false positive shows up.
