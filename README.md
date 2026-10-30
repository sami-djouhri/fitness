# fitness

![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white)
![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)

Training log and progress: exercises, sessions, weights, repetitions, and what
has changed over the weeks. Part of the
[Saganta Suite](https://github.com/sami-djouhri/saganta-suite), usable on its
own. All user-facing text is German.

## The point of it inside the suite

Training is the part of a week that gets displaced first, so it is worth having
in the same place as everything else that competes for the same evening. The
calendar's habit scheduler can place sessions; this is where they are recorded
and where progress is read back.

Standalone it is a training log that happens to have an HTTP API.

## Configuration

Everything is passed in through the environment. This service has **no**
`env_file`, so every value has to be listed in the compose file explicitly. A
value written into a `.env` next to it looks set and never reaches the
container.

## Tests

```bash
./run-tests.sh
```

The runner states the number of tests it expects. That is not decoration: twelve
tests here were broken for weeks and the suite still reported success, because a
run with fewer tests looks exactly like a run with all of them.

## License

AGPL-3.0.

## About this snapshot

The recipe, not the data. The home-network compose overlay is not in here.

The development history stays private; the public one starts at the first
release and grows with each one.
