from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Tuple
import json, numpy as np
from pathlib import Path

@dataclass
class Record:
    id: str
    text: str
    meta: Dict[str, Any]

class SimpleVectorStore:
    def __init__(self, dir_path: str = ".rag_index"):
        self.dir = Path(dir_path); self.dir.mkdir(parents=True, exist_ok=True)
        self.vec_path = self.dir / "vectors.npy"
        self.meta_path = self.dir / "meta.jsonl"
        self._vecs = None; self._meta: List[Record] = []
        if self.vec_path.exists() and self.meta_path.exists():
            self._vecs = np.load(self.vec_path)
            with self.meta_path.open() as f:
                for line in f: self._meta.append(Record(**json.loads(line)))

    def add(self, embeddings: List[List[float]], records: List[Record]):
        vecs = np.array(embeddings, dtype="float32")
        self._vecs = vecs if self._vecs is None else np.vstack([self._vecs, vecs])
        with self.meta_path.open("a") as f:
            for r in records: f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n"); self._meta.append(r)
        np.save(self.vec_path, self._vecs)

    def search(self, qvec: List[float], k: int = 5) -> List[Tuple[float, Record]]:
        if self._vecs is None: return []
        A = self._vecs / (np.linalg.norm(self._vecs, axis=1, keepdims=True) + 1e-9)
        q = np.array(qvec, dtype="float32"); q = q / (np.linalg.norm(q) + 1e-9)
        sims = A @ q; idx = np.argsort(-sims)[:k]
        return [(float(sims[i]), self._meta[i]) for i in idx]