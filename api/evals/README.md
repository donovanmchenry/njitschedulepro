# AI schedule description evaluation

This suite sends 30 deliberately messy student descriptions through the same
`parse_natural_language` model call and Pydantic validation used by
`POST /ai/parse-schedule`. It calls the parser directly so a development run does
not weaken or consume the public endpoint's per-student rate limit.

Run it from `api/`:

```bash
python3 scripts/evaluate_ai_descriptions.py --concurrency 4
```

The command requires `ANTHROPIC_API_KEY` and writes `latest-results.json` plus a
short `latest-results.md`. An exact result matches every asserted field; partial
means the valid response matched at least one field but missed another; fail means
the response errored or matched no asserted fields.

## Catalog sources

Cases use current NJIT catalog terminology and real course keys from:

- [B.S. in Computer Science](https://catalog.njit.edu/undergraduate/computing-sciences/computer-science/bs/)
- [Data Science courses](https://catalog.njit.edu/undergraduate/computing-sciences/data-science/)
- [B.S. in Information Technology](https://catalog.njit.edu/undergraduate/computing-sciences/informatics/bs/)
- [AI minor for CS and DS majors](https://catalog.njit.edu/undergraduate/computing-sciences/data-science/artificial-intelligence-minor-cs-ds-majors/)
- [Computing Literacy GER](https://catalog.njit.edu/undergraduate/academic-policies-procedures/general-education-requirements/computer-science-ger/)
