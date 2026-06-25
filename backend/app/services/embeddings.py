"""
Embedding Service
Uses local SentenceTransformer (all-MiniLM-L6-v2 → 384-dim) to match
the existing Pinecone index dimension.
Model is loaded lazily on first use and cached for subsequent calls.
"""

import os
import logging
from app.config import HUGGINGFACE_EMBEDDING_MODEL

os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)


class EmbeddingModel:
    """
    Lazy-loading sentence-transformer wrapper.
    The model is only loaded on the first embed_query() call,
    keeping server startup fast.
    """

    def __init__(self):
        self._model = None

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            model_name = HUGGINGFACE_EMBEDDING_MODEL or "all-MiniLM-L6-v2"
            print(f"[INFO] Loading embedding model '{model_name}' on first use...")
            self._model = SentenceTransformer(model_name)
            print(f"[INFO] Embedding model ready.")
        return self._model

    def embed_query(self, text: str) -> list[float]:
        model = self._load_model()
        return model.encode(text).tolist()


embedding_model = EmbeddingModel()