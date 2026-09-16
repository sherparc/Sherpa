---
name: regenerate-django-migrations
description: "Regenerate Django Migrations output in svc/pay/pay/migrations instead of editing generated files. Use when a change touches the sources or configs listed in this skill."
---

# regenerate-django-migrations

> Generated code is regenerated, not explained (ADR-0011): the knowledge lives in the sources and the
> generator, never in the output.

<!-- sherpa:begin facts -->
## facts (origin/main@REV, as of 2026-03-01)

| field | value |
|---|---|
| family | Django Migrations (`django-migrations`) |
| home | `svc/pay/pay/migrations` |
| generated files | 6 (6 LOC) |
| sources | `svc/pay/pay/models.py` |
| configs | `svc/pay/manage.py` |
| command | `python manage.py makemigrations` |
<!-- sherpa:end facts -->

## Procedure

1. Change the source (model, schema, proto, config) — never the generated files.
2. Run the command from the facts table from the home directory; commit sources and output together.
3. Review the generated diff for surprises (renames, dropped columns, breaking changes).

## Don't

- Hand-edit a generated file: the next run overwrites it, and the fix is lost silently.
- Explain generated code in an owner doc — point to this skill instead.
