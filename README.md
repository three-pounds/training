# 3 pounds · training

> **Work in progress.** This is not medical advice. It is not a substitute for a physician.
> See a doctor before starting a training program, especially if you have a medical condition.

An MCP server that gives an AI client a deterministic, evidence-checked way to start and review a
training program. It is meant to sit next to [wger](https://github.com/wger-project/wger)'s MCP
server, which holds the data. Licensed AGPL-3.0-or-later.

## What it does

The reasoning happens in your MCP client. This server never calls a language model and holds no
model keys. It exposes:

- `screen_readiness`: applies the outcome of the official [PAR-Q+](https://www.eparmedx.com) from
  the question numbers you answered yes to. A yes to question 2 or 7 stops the design and
  recommends a physician. The server never reproduces the questionnaire; you complete it on the
  official site.
- `assess_decision_basis`: checks whether the variables that justified a program's methodology
  still hold. If one moved beyond its tolerance, only a full redesign is allowed, never a patch.
- `reevaluate_body_composition`: decides the next step after body-composition scans in a fixed
  order (verify the scan, loss rate, protein, strength, methodology last). Nutrition findings are
  handed off, never prescribed.
- `check_decision_citations`: rejects a decision that cites nothing or cites a source that is not
  in the evidence registry, and flags sources that conflict or do not apply to the person.
- Prompts `nuevo-programa` and `revisar-semana`, which open with the medical notice and walk the
  client through these tools.

## Safety: a single layer

Safety here is one layer: the screening above and the method. There is no second check in the
tool that writes to wger, and none exists until wger accepts one upstream. This version does not
write to wger at all. The AGPL "no warranty" clause protects the author, not someone who hosts
this service for other people.

## Supported clients

Built for Claude (claude.ai and Desktop) and Claude Code. End-to-end testing in those clients is
still pending. No promise is made for other clients.

## Run

```
uv run threepounds-training
```

This starts the server over stdio.

## Contributing

Never put personal data in this repository. A CI check blocks a configured list of names and
terms.
