# papers

PDF mirrors of my academic papers, hosted for direct download and for embedding in blog posts at [danieltan.omg.lol](https://danieltan.omg.lol).

Each file is a mirror. The canonical archive for every paper is on Zenodo under its own DOI; peer-reviewed versions are at their journal of record. This repo exists so readers do not have to leave the blog to view a PDF, and so the viewer embed on each blog post has a CORS-friendly, iframe-friendly source.

## Index

| Slug | Title | DOI / venue | Series |
|---|---|---|---|
| `qft-observer-elimination.pdf` | Observers in quantum field theory cannot be fundamental excitations | IJQF 2026 &middot; [10.5281/zenodo.21672643](https://doi.org/10.5281/zenodo.21672643) | Quantum Observers, 1 of 3 |
| `qft-observer-mechanism.pdf` | Fermionic Matter Currents as the QFT Observer Mechanism | Quantum Reports 2026 &middot; [10.3390/quantum8040106](https://doi.org/10.3390/quantum8040106) &middot; [10.5281/zenodo.21900457](https://doi.org/10.5281/zenodo.21900457) | Quantum Observers, 2 of 3 |
| `qft-observer-updating.pdf` | Selecting unique outcomes in spacetime through matter currents | Drafting | Quantum Observers, 3 of 3 |
| `master-equation.pdf` | Spacetime as a Functional of Matter | SHPS (under review) | Wave Relativity, 1 of 3 |
| `classical-prejudice-in-quantum-gravity.pdf` | Classical Prejudice in Quantum Gravity | GRF 2027 submission (DOI pending) | Wave Relativity, 2 of 3 |
| `grf-essay-gravity-always-quantum.pdf` | Gravity has always been quantum mechanical | Zenodo v1.2 &middot; [10.5281/zenodo.21193435](https://doi.org/10.5281/zenodo.21193435) | Wave Relativity, 3 of 3 |
| `matter-wave-internal-structure.pdf` | Matter-wave internal structure selects U(1)xSU(2)xSU(3) | Drafting, IJMPA target | Matter-Wave Field, 1 of 2 |
| `capacity-fragility-indicator.pdf` | Capacity Fragility Indicator | Drafting | People as Foundation, 1 of &hellip; |

## Not the citation URL

Cite the Zenodo DOI, not the GitHub Pages URL. This repo may move, the DOI will not.

## scripts/paper-to-blog.py

Converts a pandoc-markdown paper (`draft.md` + `refs.bib` + numeric-brackets CSL) into KaTeX-friendly HTML suitable for the omg.lol blog. Handles `\begin{equation}`/`\eqref`/`\hyperref`/`\phantomsection`/`\label`, resolves citations against the BibTeX file, and emits anchor-style cite tags matching the blog's convention. Usage:

```sh
python3 scripts/paper-to-blog.py \
  --draft /path/to/draft.md \
  --bib   /path/to/refs.bib \
  --csl   /path/to/numeric-brackets.csl \
  > body.html
```

Then prepend a paper-landing header (title, series badge, metadata block, abstract) and POST to `/weblog/entry/<id>`.
