from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

import cv2
import numpy as np


def load_runtime(runtime: Path):
    sys.path.insert(0, str(runtime))
    import clip_runner as cr
    return cr


def load_model(cr, runtime: Path):
    return cr.load_model(runtime / "ViT-B-32.pt", verify=True)


def image_feature(cr, model, path: Path) -> np.ndarray:
    import torch
    image = cr.preprocess_image(path)
    with torch.inference_mode():
        feature = cr.normalize_features(model.encode_image(image))
    return feature.detach().cpu().numpy().astype("float32")[0]


def text_feature(cr, model, runtime: Path, text: str) -> np.ndarray:
    import torch
    tokenizer = cr.SimpleTokenizer(runtime / "bpe_simple_vocab_16e6.txt.gz")
    with torch.inference_mode():
        feature = cr.normalize_features(model.encode_text(tokenizer.tokenize([text])))
    return feature.detach().cpu().numpy().astype("float32")[0]


def collapse(view_scores: np.ndarray, owners: np.ndarray, n_objects: int) -> np.ndarray:
    output = np.full(n_objects, -10, np.float32)
    np.maximum.at(output, owners, view_scores)
    return output


def normalize_01(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, np.float32)
    lo, hi = float(values.min()), float(values.max())
    return (values - lo) / (hi - lo + 1e-9)


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower().replace("-", " "))


def bm25_object_scores(objects: list[dict], query: str) -> np.ndarray:
    docs: list[list[str]] = []
    raws: list[str] = []
    for obj in objects:
        label = obj.get("label", "") or ""
        context = obj.get("structural_context") or obj.get("context") or obj.get("scope_title") or ""
        title = (obj.get("title", "") or "") if obj.get("caption_text_quality", "usable") == "usable" else ""
        raw = (label + " ") * 2 + (title + " ") * 2 + context
        raws.append(raw)
        docs.append(tokenize(raw))
    if not docs:
        return np.zeros(0, np.float32)
    n_docs = len(docs)
    df = Counter()
    for doc in docs:
        df.update(set(doc))
    avg_len = sum(map(len, docs)) / n_docs
    k1, b = 1.4, 0.75
    query_tokens = tokenize(query)
    normalized_query = " ".join(query_tokens)
    scores = np.zeros(n_docs, np.float32)
    for i, doc in enumerate(docs):
        tf = Counter(doc)
        for token in query_tokens:
            freq = tf[token]
            if not freq:
                continue
            idf = math.log(1 + (n_docs - df[token] + 0.5) / (df[token] + 0.5))
            scores[i] += idf * freq * (k1 + 1) / (
                freq + k1 * (1 - b + b * len(doc) / max(avg_len, 1e-9))
            )
        if normalized_query and normalized_query in " ".join(tokenize(raws[i])):
            scores[i] += 8.0
    return scores


def result_row(obj: dict, score: float, **extra) -> dict:
    row = {
        "score": round(float(score), 6),
        "corpus": obj.get("corpus_id"),
        "kind": obj.get("kind"),
        "label": obj.get("label"),
        "title": obj.get("title", ""),
        "page": obj.get("page"),
        "occurrence_id": obj.get("occurrence_id"),
        "logical_visual_id": obj.get("logical_visual_id"),
    }
    row.update(extra)
    return row


def load_figure_index(root: Path):
    index_root = root / "figure_index"
    objects = [json.loads(line) for line in (index_root / "objects.jsonl").read_text(encoding="utf-8").splitlines() if line]
    visual = np.load(index_root / "view_embeddings.npy", mmap_mode="r")
    text = np.load(index_root / "text_embeddings.npy", mmap_mode="r")
    owners = np.load(index_root / "view_owner.npy", mmap_mode="r")
    names = [json.loads(line) for line in (index_root / "view_names.jsonl").read_text(encoding="utf-8").splitlines() if line]
    return index_root, objects, visual, text, owners, names


def figure_image(args, cr, model, root: Path) -> dict:
    _, objects, visual, _, owners, _ = load_figure_index(root)
    query = image_feature(cr, model, Path(args.image))
    scores = collapse(np.asarray(visual) @ query, np.asarray(owners), len(objects))
    mask = np.ones(len(objects), bool)
    if args.exclude_corpus:
        mask &= np.array([obj.get("corpus_id") != args.exclude_corpus for obj in objects])
    order = np.argsort(-np.where(mask, scores, -99))[: args.k]
    return {
        "mode": "figure_image_semantic",
        "claim_boundary": "visual similarity retrieves candidates; it does not establish engineering equivalence",
        "results": [result_row(objects[i], scores[i], visual_similarity=round(float(scores[i]), 6)) for i in order],
    }


def figure_text(args, cr, model, root: Path) -> dict:
    _, objects, visual, text_embeddings, owners, _ = load_figure_index(root)
    query = text_feature(cr, model, Path(args.runtime), args.query)
    context = np.asarray(text_embeddings) @ query
    visual = collapse(np.asarray(visual) @ query, np.asarray(owners), len(objects))
    lexical = bm25_object_scores(objects, args.query)
    if float(lexical.max(initial=0.0)) > 0:
        weights = {"lexical": 0.55, "context_semantic": 0.35, "visual_semantic": 0.10}
    else:
        weights = {"lexical": 0.0, "context_semantic": 0.80, "visual_semantic": 0.20}
    score = (
        weights["lexical"] * normalize_01(lexical)
        + weights["context_semantic"] * normalize_01(context)
        + weights["visual_semantic"] * normalize_01(visual)
    )
    order = np.argsort(-score)[: args.k]
    return {
        "mode": "figure_text_retrieval",
        "query": args.query,
        "weights": weights,
        "results": [
            result_row(
                objects[i], score[i],
                lexical=round(float(lexical[i]), 6),
                context_semantic=round(float(context[i]), 6),
                visual_semantic=round(float(visual[i]), 6),
            )
            for i in order
        ],
    }


def figure_related(args, cr, model, root: Path) -> dict:
    _, objects, visual, text_embeddings, owners, names = load_figure_index(root)
    candidates = [
        i for i, obj in enumerate(objects)
        if obj.get("corpus_id") == args.corpus and str(obj.get("label")) == args.label
    ]
    if not candidates:
        raise SystemExit("source object not found")
    source_index = candidates[0]
    global_view_index = next(
        (i for i, item in enumerate(names) if item["object_index"] == source_index and item["view"] == "global"),
        None,
    )
    if global_view_index is None:
        raise SystemExit("source object has no global view")
    query_visual = np.asarray(visual[global_view_index])
    visual_scores = collapse(np.asarray(visual) @ query_visual, np.asarray(owners), len(objects))
    context_scores = np.asarray(text_embeddings) @ np.asarray(text_embeddings[source_index])
    score = 0.55 * visual_scores + 0.45 * context_scores
    mask = np.ones(len(objects), bool)
    mask[source_index] = False
    if args.cross_corpus:
        mask &= np.array([obj.get("corpus_id") != args.corpus for obj in objects])
    order = np.argsort(-np.where(mask, score, -99))[: args.k]
    return {
        "mode": "cross_corpus_candidate_similarity" if args.cross_corpus else "figure_candidate_similarity",
        "claim_boundary": "candidate generation only; similarity does not establish semantic or engineering equivalence",
        "source": result_row(objects[source_index], 1.0),
        "results": [
            result_row(
                objects[i], score[i],
                visual_similarity=round(float(visual_scores[i]), 6),
                context_similarity=round(float(context_scores[i]), 6),
            )
            for i in order
        ],
    }


def page_image(args, cr, model, root: Path) -> dict:
    namespace_root = root / "page_indexes" / args.namespace
    objects = [json.loads(line) for line in (namespace_root / "objects.jsonl").read_text(encoding="utf-8").splitlines() if line]
    base = np.load(namespace_root / "view_image_embeddings.npy", mmap_mode="r").reshape(len(objects), 6, 512)
    parts = [np.asarray(base)]
    fine = namespace_root / "fine_50_embeddings.npy"
    if fine.exists():
        parts.append(np.load(fine, mmap_mode="r").reshape(len(objects), 5, 512))
    views = np.concatenate(parts, axis=1)
    query = image_feature(cr, model, Path(args.image))
    clip_scores = np.einsum("ovd,d->ov", views, query).max(axis=1)
    order = np.argsort(-clip_scores)
    if args.mode == "semantic":
        selected = order[: args.k]
        return {
            "mode": "page_visual_semantic",
            "namespace": args.namespace,
            "results": [result_row(objects[i], clip_scores[i], visual_similarity=round(float(clip_scores[i]), 6)) for i in selected],
        }

    shortlist = order[: args.shortlist]
    descriptors = np.load(namespace_root / "orb_descriptors.npy", mmap_mode="r")
    owners = np.load(namespace_root / "orb_owners.npy", mmap_mode="r")
    image = cv2.imread(args.image, 0)
    if image is None:
        raise SystemExit("unable to read query image")
    if image.shape[1] > 650:
        scale = 650 / image.shape[1]
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    orb = cv2.ORB_create(nfeatures=500, scaleFactor=1.2, nlevels=8, fastThreshold=12)
    _, query_descriptors = orb.detectAndCompute(image, None)
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
    local_scores: list[float] = []
    for candidate in shortlist:
        candidate_descriptors = np.asarray(descriptors[np.asarray(owners) == candidate])
        local_score = 0.0
        if query_descriptors is not None and len(query_descriptors) > 2 and len(candidate_descriptors) > 2:
            good: list[float] = []
            for pair in matcher.knnMatch(query_descriptors, candidate_descriptors, k=2):
                if len(pair) < 2:
                    continue
                first, second = pair
                if first.distance < 0.82 * second.distance:
                    good.append(1 - first.distance / max(1, second.distance))
            if good:
                local_score = len(good) + sum(good)
        local_scores.append(local_score)
    reranked = shortlist[np.argsort(-np.asarray(local_scores))]
    local_by_object = {int(candidate): float(score) for candidate, score in zip(shortlist, local_scores)}
    selected = reranked[: args.k]
    return {
        "mode": "page_source_reidentification",
        "namespace": args.namespace,
        "shortlist": args.shortlist,
        "method": "CLIP semantic shortlist -> ORB local-feature rerank",
        "claim_boundary": "source re-identification ranks likely source occurrences; it does not interpret engineering meaning",
        "results": [
            result_row(
                objects[i], local_by_object[i],
                local_feature_score=round(local_by_object[i], 6),
                clip_similarity=round(float(clip_scores[i]), 6),
                clip_shortlist_rank=int(np.where(shortlist == i)[0][0]) + 1,
            )
            for i in selected
        ],
    }


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Search a private Engineering Visual Memory index")
    ap.add_argument("--index", required=True, type=Path)
    ap.add_argument("--runtime", required=True, type=Path)
    sub = ap.add_subparsers(dest="command", required=True)

    image = sub.add_parser("figure-image")
    image.add_argument("image")
    image.add_argument("-k", type=int, default=10)
    image.add_argument("--exclude-corpus")

    text = sub.add_parser("figure-text")
    text.add_argument("query")
    text.add_argument("-k", type=int, default=10)

    related = sub.add_parser("figure-related")
    related.add_argument("corpus")
    related.add_argument("label")
    related.add_argument("-k", type=int, default=10)
    related.add_argument("--cross-corpus", action="store_true")

    page = sub.add_parser("page-image")
    page.add_argument("namespace")
    page.add_argument("image")
    page.add_argument("--mode", choices=("semantic", "source"), default="source")
    page.add_argument("--shortlist", type=int, default=50)
    page.add_argument("-k", type=int, default=10)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    cr = load_runtime(args.runtime)
    model = load_model(cr, args.runtime)
    handlers = {
        "figure-image": figure_image,
        "figure-text": figure_text,
        "figure-related": figure_related,
        "page-image": page_image,
    }
    result = handlers[args.command](args, cr, model, args.index)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
