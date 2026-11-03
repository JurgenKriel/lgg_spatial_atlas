# Paper analysis

Code behind the figures and tables in the paper that accompanies the atlas.

## Layout

One folder per figure, so a reader can go from a panel straight to its code:

```
analysis/
├── technology (st/sm/snRNA)/
│   ├── README.md      which figures this is related to
│   ├── *.py | *.R     the scripts
│   └── outputs/       generated figures/tables (git-ignored)
├── technology /
└── supplementary/
```

## Conventions

- **Inputs are not committed.** 
- **Outputs are regenerated, not stored.** Anything under `outputs/` is
  git-ignored. Final figure files go in the paper, not here.
- **Record the environment.** Pin package versions (`requirements.txt`,
  `renv.lock` or `sessionInfo()` output) next to the scripts that need them.
