# Problem set

25 problems drawn from *Math & Computation Using Python*: numerical integration,
root finding, matrix operations, series summation, prime sieves, string
processing, file I/O, recursion, simple plotting.

One directory per problem, id in `snake_case`:

```
data/problems/trapezoid_integration/
├── problem.yaml        # id, title, statement, misconceptions_applicable, tags
├── reference.py        # the correct solution; mutations are applied to its AST
└── tests.py            # 5-10 cases, each tagged normal | edge | boundary | degenerate
```

`problem.yaml` fields:

| Field | Purpose |
|---|---|
| `id` | Must match the directory name |
| `statement` | Shown to the model as trusted context |
| `misconceptions_applicable` | Which taxonomy codes this problem can express — an operator that does not apply is skipped rather than forced |
| `tags` | Topic, for stratifying the eval set |

Test kinds are load-bearing: `agent/aggregate.py` weights them per
`rubric/rubric.yaml`, and mutation severity is derived from *which* kinds a
mutation breaks. A problem whose tests are all `normal` cannot distinguish an
edge-case misconception from a correct solution, so include at least one `edge`
and one `boundary` case each.
