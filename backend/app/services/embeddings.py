import os
import logging
from app.config import HUGGINGFACE_EMBEDDING_MODEL
from sentence_transformers import SentenceTransformer

os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)


class EmbeddingModel:
    def __init__(self):
        self._model = None

    def _load_model(self):
        if self._model is None:
            self._model = SentenceTransformer(HUGGINGFACE_EMBEDDING_MODEL)
        return self._model

    def embed_query(self, text):
        model = self._load_model()
        return model.encode(text).tolist()


embedding_model = EmbeddingModel()