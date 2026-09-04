# CLAUDE.md

Guidance for working in this repo. See `README.md` for the pipeline
overview and `lab_notebook.ipynb`'s Abstract cell for the authoritative,
up-to-date summary.

## Ground rules

- `downloads/` is fixed and read-only -- never write into it, never treat
  it as scratch space. It's the source of truth everything else derives
  from.
- All derived output goes to `processed/`, never back into `downloads/`.
- `lab_notebook.ipynb` is the record of every transformation. Each work
  session gets its own dated `##` markdown section. When editing the
  notebook, use the `jupyter-notebook` skill -- it covers plot style,
  legends, table rendering, the two-pass authoring workflow, and the
  execution-hygiene bugs below in more detail.
- The notebook is large enough (embedded PNGs) that the `Read` tool can
  choke on it, which blocks `NotebookEdit`. If that happens, edit via
  `nbformat` directly (read, modify `.source` by cell id, write) instead.

## Known gotchas

- **Kernel pinning.** `jupyter nbconvert --execute` can silently bind to
  the wrong environment. Always pass
  `--ExecutePreprocessor.kernel_name=python3` and check
  `nb.metadata["kernelspec"]`.
- **Idempotency.** Expensive build cells (the raw matrix, the ARACNe base
  matrix) must guard with `if out_path.exists(): skip`, or a routine
  notebook re-run silently rebuilds them and invalidates "untouched since
  built" claims.
- **Backgrounding long runs.** Background the actual long command
  directly -- don't `nohup ... &` it inside an already-backgrounded shell
  call, or the completion notification is for the wrapper, not the real
  job.
- **pandas Categorical columns.** AnnData auto-converts `obs` string
  columns to Categorical on save/load. Chained `.str.split().str[...]`
  and `.map(dict)` both misbehave on Categorical dtype -- cast with
  `.astype(str)` first.
- **CPM denominator.** Protein-coding genes are ~33% of the annotated gene
  count but ~97% of total reads in a typical sample, and that ratio isn't
  constant across samples. Any CPM calculation must use the *full*
  60,660-gene library size as the denominator, not a filtered subset --
  otherwise it reintroduces the exact inter-sample bias CPM exists to
  remove.
- **TMM is per-slice, not global.** Don't precompute it on the aggregated
  matrix -- compute it after slicing to a specific cohort, for a specific
  ARACNe run.

## Commits

Use the `conventional-commit` skill. Scopes are the closed vocabulary in
`SCOPES.md` -- pick one from there or omit the scope, don't invent one.
