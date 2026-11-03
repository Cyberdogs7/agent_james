import os
import json
import math
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class MemoryManager:
    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.memory_file = self.project_path / "memory.jsonl"
        self.client = None  # embeddings are local-first (see backend/embeddings.py)

    def _get_embedding(self, text):
        try:
            from backend.embeddings import embed_sync
        except ImportError:
            try:
                from embeddings import embed_sync
            except ImportError:
                return None
        try:
            return embed_sync(text)
        except Exception as e:
            print(f"[MemoryManager] Embedding failed: {e}")
            return None

    def add_memory(self, content, tags=None):
        if tags is None:
            tags = []

        embedding = self._get_embedding(content)

        entry = {
            "timestamp": time.time(),
            "content": content,
            "tags": tags,
            "embedding": embedding
        }

        # Ensure project dir exists (should already, but safety first)
        if not self.project_path.exists():
            return False, "Project path does not exist."

        try:
            with open(self.memory_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
            return True, "Memory added."
        except Exception as e:
            return False, f"Failed to save memory: {e}"

    def _cosine_similarity(self, vec1, vec2):
        if not vec1 or not vec2:
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def search_memory(self, query, limit=5):
        if not self.memory_file.exists():
            return []

        memories = []
        try:
            with open(self.memory_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        memories.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"[MemoryManager] Error reading memory file: {e}")
            return []

        query_embedding = self._get_embedding(query)

        scored_memories = []

        for mem in memories:
            score = 0.0
            if query_embedding and mem.get("embedding"):
                score = self._cosine_similarity(query_embedding, mem["embedding"])
            else:
                # Fallback: Keyword matching
                q_tokens = set(query.lower().split())
                c_tokens = set(mem.get("content", "").lower().split())
                if not q_tokens:
                    score = 0.0
                else:
                    overlap = len(q_tokens.intersection(c_tokens))
                    score = overlap / len(q_tokens)

            scored_memories.append((score, mem))

        # Sort by score descending
        scored_memories.sort(key=lambda x: x[0], reverse=True)

        # Return top N content
        results = []
        for score, mem in scored_memories[:limit]:
            # Filter out very low scores?
            # Let's say if score > 0.
            if score > 0.0:
                 results.append(mem.get("content", ""))

        return results
