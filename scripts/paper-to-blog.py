#!/usr/bin/env python3
"""
Convert a pandoc-markdown paper (draft.md + refs.bib + CSL) into a KaTeX-friendly
blog post body for omg.lol.

Input:  --draft <path>    paper draft.md with pandoc citations @key
        --bib <path>      refs.bib (BibTeX)
        --csl <path>      numeric-brackets CSL
Output: writes the HTML body to stdout.

Transformations:
  1. Pandoc --citeproc produces numeric citations like [1] with references at end.
  2. \\begin{equation}...\\end{equation} blocks become $$ ... \\tag{N} $$ with
     tracked labels. Equation numbers map to IDs for cross-ref links.
  3. \\eqref{eq:X} becomes <a href="#eq-N">(N)</a>.
  4. \\phantomsection\\label{X} becomes <span id="X"></span>.
  5. Citations and references get the blog's <a id="cite-N-M" href="#refN"> format.
"""

import argparse
import re
import subprocess
import sys


def strip_yaml_frontmatter(text):
    """Remove the --- ... --- block at the top of the draft."""
    m = re.match(r'^---\n.*?\n---\n', text, flags=re.DOTALL)
    return text[m.end():] if m else text


def extract_math_and_mask(text):
    """Pull math blocks out before pandoc sees them, so pandoc doesn't interfere."""
    stash = []

    def stash_one(match, kind):
        stash.append((kind, match.group(0)))
        return f"\x00MATH_{len(stash)-1}\x00"

    def display_math(m): return stash_one(m, 'display')
    def equation_env(m): return stash_one(m, 'equation')
    def eqalign_env(m): return stash_one(m, 'eqalign')
    def inline(m): return stash_one(m, 'inline')
    def eqref(m): return stash_one(m, 'eqref')
    def phantom(m): return stash_one(m, 'phantom')

    def hyperref(m): return stash_one(m, 'hyperref')

    # Order matters: longer patterns first.
    text = re.sub(r'\\phantomsection\\label\{([^}]+)\}', phantom, text)
    text = re.sub(r'\\begin\{equation\}(.*?)\\end\{equation\}',
                  equation_env, text, flags=re.DOTALL)
    text = re.sub(r'\\begin\{align(?:\*|ed)?\}(.*?)\\end\{align(?:\*|ed)?\}',
                  eqalign_env, text, flags=re.DOTALL)
    text = re.sub(r'\\eqref\{([^}]+)\}', eqref, text)
    text = re.sub(r'\\hyperref\[([^]]+)\]\{([^}]+)\}', hyperref, text)
    text = re.sub(r'\$\$(.+?)\$\$', display_math, text, flags=re.DOTALL)
    text = re.sub(r'(?<!\$)\$([^$\n]+?)\$', inline, text)
    return text, stash


def restore_math(text, stash, eq_table):
    """Put math back after pandoc processing, converting to KaTeX-friendly form."""
    eq_counter = [0]

    def restore_one(match):
        idx = int(match.group(1))
        kind, original = stash[idx]
        if kind == 'inline':
            return original  # $...$ passes through to KaTeX
        if kind == 'display':
            return original  # $$...$$ passes through
        if kind == 'equation':
            eq_counter[0] += 1
            n = eq_counter[0]
            inner = re.search(r'\\begin\{equation\}(.*?)\\end\{equation\}',
                              original, flags=re.DOTALL).group(1)
            # Pull any \label{X} out of the inner, record the mapping.
            label_m = re.search(r'\\label\{([^}]+)\}', inner)
            if label_m:
                eq_table[label_m.group(1)] = n
                inner = re.sub(r'\\label\{[^}]+\}', '', inner)
            inner = inner.strip()
            id_attr = f' id="eq-{n}"'
            return (f'<div class="equation-block"{id_attr}>\n'
                    f'$$\n{inner}\n\\tag{{{n}}}\n$$\n</div>')
        if kind == 'eqalign':
            # align blocks: keep as display, no numbering for prototype
            inner = re.search(
                r'\\begin\{align(?:\*|ed)?\}(.*?)\\end\{align(?:\*|ed)?\}',
                original, flags=re.DOTALL).group(1).strip()
            # \\ for line break; collapse labels
            inner = re.sub(r'\\label\{[^}]+\}', '', inner)
            return f'$$\n\\begin{{aligned}}\n{inner}\n\\end{{aligned}}\n$$'
        if kind == 'eqref':
            label = re.search(r'\\eqref\{([^}]+)\}', original).group(1)
            return f'<a class="eqref" data-ref="{label}">(?)</a>'
        if kind == 'phantom':
            label = re.search(r'\\phantomsection\\label\{([^}]+)\}',
                              original).group(1)
            return f'<span id="{label}"></span>'
        if kind == 'hyperref':
            m2 = re.search(r'\\hyperref\[([^]]+)\]\{([^}]+)\}', original)
            label, display = m2.group(1), m2.group(2)
            # ~ is LaTeX non-breaking space
            display = display.replace('~', '&nbsp;')
            return f'<a href="#{label}">{display}</a>'
        return original

    return re.sub(r'\x00MATH_(\d+)\x00', restore_one, text)


def resolve_eqrefs(html, eq_table):
    """Replace <a class='eqref' data-ref='X'>(?)</a> with (N) anchors."""
    def sub(m):
        label = m.group(1)
        n = eq_table.get(label)
        if n is None:
            return f'(ref:{label})'
        return f'<a href="#eq-{n}">({n})</a>'

    return re.sub(r'<a class="eqref" data-ref="([^"]+)">\(\?\)</a>', sub, html)


def run_pandoc(markdown, bib_path, csl_path):
    """Run pandoc with citeproc to resolve @ citations."""
    result = subprocess.run(
        ['pandoc',
         '--from', 'markdown',
         '--to', 'html',
         '--citeproc',
         '--bibliography', bib_path,
         '--csl', csl_path,
         '--wrap=preserve',
         '--no-highlight'],
        input=markdown, capture_output=True, text=True, check=True)
    return result.stdout


def post_process_citations(html):
    """Convert pandoc's <span class='citation'> format to blog anchor tags.

    Pandoc with a numeric CSL emits:
      <span class="citation" data-cites="k1 k2">[1,2]</span>
    or when the numbers come apart:
      <span class="citation" data-cites="k1">[1]</span>

    Target format (per classical-prejudice.essay.md convention):
      [<a id="cite-1-X" href="#ref1">1</a>,<a id="cite-2-X" href="#ref2">2</a>]
    where X is the occurrence count per cite key.
    """
    cite_count = {}

    def wrap_num(n):
        cite_count[n] = cite_count.get(n, 0) + 1
        occ = cite_count[n]
        return f'<a id="cite-{n}-{occ}" href="#ref{n}">{n}</a>'

    def rewrite_citation(m):
        cite_keys = m.group(1).split()
        text = m.group(2).strip()
        # Strip outer brackets, work on inner text.
        inner_m = re.match(r'^\[(.*)\]$', text, flags=re.DOTALL)
        if not inner_m:
            return text
        inner = inner_m.group(1)
        # Split by top-level semicolons (multi-citation with locators), then by
        # commas if no semicolons. Each chunk should start with a number.
        if ';' in inner:
            chunks = [c.strip() for c in inner.split(';')]
        else:
            # If chunks come from a plain [1,2,3] list with N keys and N numbers,
            # split on commas. If there are more commas than keys, the extras
            # belong to a locator on the first number.
            parts = [p.strip() for p in inner.split(',')]
            if len(cite_keys) == 1 or len(parts) != len(cite_keys):
                # Treat the whole thing as "N, locator text"
                chunks = [inner.strip()]
            else:
                chunks = parts

        rewritten = []
        for chunk in chunks:
            num_m = re.match(r'^(\d+)(.*)$', chunk, flags=re.DOTALL)
            if num_m:
                n = int(num_m.group(1))
                rest = num_m.group(2)
                rewritten.append(wrap_num(n) + rest)
            else:
                rewritten.append(chunk)
        joiner = '; ' if ';' in inner else (', ' if ',' in inner and len(chunks) > 1 else '')
        if not joiner:
            return '[' + rewritten[0] + ']'
        return '[' + joiner.join(rewritten) + ']'

    html = re.sub(
        r'<span class="citation"[^>]*data-cites="([^"]+)"[^>]*>(\[[^\]]+\])</span>',
        rewrite_citation, html, flags=re.DOTALL)
    return html


def post_process_references(html):
    """Convert pandoc's references div to a numbered list with <li id='refN'>.

    Pandoc + CSL emits:
      <div id="refs" class="references csl-bib-body" ...>
        <div id="ref-key" class="csl-entry" role="listitem">
          <div class="csl-left-margin">1. </div>
          <div class="csl-right-inline">Full reference text...</div>
        </div>
        ...
      </div>
    """
    def process_refs_div(m):
        body = m.group(1)
        # Each csl-entry contains left-margin + right-inline. Capture both inner divs.
        entries = re.findall(
            r'<div id="ref-[^"]+" class="csl-entry"[^>]*>\s*'
            r'<div class="csl-left-margin">[^<]*</div>\s*'
            r'<div class="csl-right-inline">(.*?)</div>\s*'
            r'</div>',
            body, flags=re.DOTALL)
        if not entries:
            # Fallback: naive single-div entries
            entries = re.findall(
                r'<div id="ref-[^"]+" class="csl-entry"[^>]*>(.*?)</div>\s*(?=<div id="ref|</div>)',
                body, flags=re.DOTALL)
        lines = ['\n<h2>References</h2>\n<ol class="references">']
        for i, entry in enumerate(entries, 1):
            cleaned = entry.strip()
            cleaned = re.sub(r'^\s*\[?\d+\.?\]?\s*', '', cleaned)
            lines.append(f'<li id="ref{i}">{cleaned}</li>')
        lines.append('</ol>')
        return '\n'.join(lines)

    html = re.sub(
        r'<div id="refs"[^>]*>(.*?)</div>\s*$',
        process_refs_div, html, flags=re.DOTALL)
    return html


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--draft', required=True)
    ap.add_argument('--bib', required=True)
    ap.add_argument('--csl', required=True)
    args = ap.parse_args()

    with open(args.draft) as f:
        raw = f.read()

    body = strip_yaml_frontmatter(raw)
    masked, stash = extract_math_and_mask(body)

    # Also strip LaTeX \setcounter and other header-only noise just in case
    masked = re.sub(r'\\setcounter\{[^}]+\}\{[^}]+\}', '', masked)
    masked = re.sub(r'\\renewcommand\{[^}]+\}\{[^}]+\}', '', masked)

    html = run_pandoc(masked, args.bib, args.csl)

    eq_table = {}
    html = restore_math(html, stash, eq_table)
    html = resolve_eqrefs(html, eq_table)
    html = post_process_citations(html)
    html = post_process_references(html)
    print(html)


if __name__ == '__main__':
    main()
