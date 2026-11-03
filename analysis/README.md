# Paper analysis

Code behind the figures and tables in the paper that accompanies the atlas.

## Layout

One folder per figure, so a reader can go from a panel straight to its code:

```
analysis/
├── fig1_<short-name>/
│   ├── README.md      what the panel shows, inputs, how to run
│   ├── *.py | *.R     the scripts
│   └── outputs/       generated figures/tables (git-ignored)
├── fig2_<short-name>/
└── supplementary/
```

## Conventions

- **Inputs are not committed.** Each figure README names the data it reads and
  where that data is deposited.
- **Outputs are regenerated, not stored.** Anything under `outputs/` is
  git-ignored. Final figure files go in the paper, not here.
- **Record the environment.** Pin package versions (`requirements.txt`,
  `renv.lock` or `sessionInfo()` output) next to the scripts that need them.
