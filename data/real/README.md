# Real datasets

Downloaded, never committed (see `.gitignore`). Loaders normalise each into
`agent.schemas.Submission` with `provenance` set.

| Dataset | What it gives | Used for |
|---|---|---|
| **Menagerie** (King's College London, OSF) | 667 real CS1 submissions with **four independent human grades each** | C1 only — lets human-vs-human α be computed on the same items the agent grades, instead of cited. Java and project-scale, so not usable for the Python misconception taxonomy |
| **CodeWorkout / CSEDM** | ~57k submissions, 50 problems, correct/incorrect labels | External validity on scale and pass/fail |
| **FalconCode** | Multi-year intro-CS Python samples | Realism check against the synthetic set |

Course data from IIT Kanpur goes in `data/course/` (gitignored), only with
Prof. Verma's approval and anonymised. The project must be complete and
publishable without it — never make it a dependency.
