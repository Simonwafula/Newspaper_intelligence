from __future__ import annotations

import argparse
from pathlib import Path

from pipeline.core.io import load_pages, save_stories
from pipeline.core.linking import build_story_seeds, embedding_links, merge_stories, rule_based_links
from pipeline.core.ordering import order_blocks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", required=True, help="Path to pages.json")
    parser.add_argument("--out", required=True, help="Output stories.json")
    parser.add_argument("--min-sim", type=float, default=0.32, help="Min cosine similarity")
    args = parser.parse_args()

    pages = load_pages(args.pages)

    for page in pages:
        page.blocks = order_blocks(page.blocks)

    seeds = build_story_seeds(pages)
    links = rule_based_links(seeds)
    links.extend(embedding_links(seeds, min_similarity=args.min_sim))
    stories = merge_stories(seeds, links)

    save_stories(args.out, stories)
    print(f"Wrote {len(stories)} stories -> {args.out}")


if __name__ == "__main__":
    main()
