from typing import List
import re

def split_text(text: str, max_tokens: int = 500) -> List[str]:
    # Simple sentence-ish splitter; swap for tiktoken-based when needed
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, cur, count = [], [], 0
    for para in paras:
        sents = re.split(r'(?<=[.!?])\s+', para)
        for s in sents:
            toks = s.split()
            if count + len(toks) > max_tokens and cur:
                chunks.append(" ".join(cur))
                cur, count = [], 0
            cur.append(s)
            count += len(toks)
    if cur:
        chunks.append(" ".join(cur))
    return chunks