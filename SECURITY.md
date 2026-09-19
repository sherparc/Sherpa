# Security policy

Sherpa writes files into your repository (`sherpa apply`) and installs a hook that runs on every Claude Code
turn (`.claude/hooks/sherpa-outcome.py`). That is the surface that matters:

- `apply` writing outside its own markers, through a symlink, or over a file that changed since the preview
  (ADR-0016, ADR-0030 to ADR-0033);
- a path from a plan, a manifest or a git path that escapes the repository;
- the outcome hook or the checker executing anything but what they ship with;
- `self-update` installing something other than the release it names.

Anything of that kind is a vulnerability, not a bug report.

## Reporting

Report privately — not in a public issue — through
[GitHub's private vulnerability reporting](https://github.com/sherparc/Sherpa/security/advisories/new) or by
email to a.chirila87@gmail.com. Include the Sherpa version (`sherpa --version`), the command, and a way to
reproduce it on a fixture repository (never on a private one). You will hear back within seven days; a fix
ships as a patch release with a GitHub Security Advisory that credits you unless you prefer otherwise.

## Supported versions

The latest tagged release only (`sherpa self-update` installs it). Releases are not patched retroactively.
