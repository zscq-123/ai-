"""向量化后端。

默认使用 fastembed + BGE-small-zh，本地 ONNX 推理：不联网、无调用费。
首次使用需要下载模型（约 100 MB），之后可完全离线运行。
"""

import threading
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

import numpy as np
from fastembed import TextEmbedding
from numpy.typing import NDArray

FloatVector = NDArray[np.float32]
DEFAULT_EMBEDDING_CACHE_DIR = Path.home() / ".cache" / "nova" / "fastembed"


class Embedder(Protocol):
    def embed_documents(self, texts: Sequence[str]) -> list[FloatVector]: ...

    def embed_query(self, text: str) -> FloatVector: ...


class FastEmbedEmbedder:
    """BGE 中文小模型，512 维，CPU 推理。"""

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-zh-v1.5",
        *,
        cache_dir: str | None = str(DEFAULT_EMBEDDING_CACHE_DIR),
        local_files_only: bool = True,
    ) -> None:
        self._model = TextEmbedding(
            model_name=model_name,
            cache_dir=cache_dir,
            local_files_only=local_files_only,
        )

    def embed_documents(self, texts: Sequence[str]) -> list[FloatVector]:
        return [
            np.asarray(vector, dtype=np.float32)
            for vector in self._model.passage_embed(list(texts))
        ]

    def embed_query(self, text: str) -> FloatVector:
        vector = next(iter(self._model.query_embed([text])))
        return np.asarray(vector, dtype=np.float32)


def normalize(matrix: FloatVector) -> FloatVector:
    """按行归一化，长度为 0 的行保持为 0。"""

    norms = np.linalg.norm(matrix, axis=-1, keepdims=True)
    norms[norms == 0] = 1.0
    return (matrix / norms).astype(np.float32)


class LazyFastEmbedEmbedder:
    """首次调用时才加载模型，避免拖慢服务启动。"""

    def __init__(
        self,
        model_name: str,
        *,
        cache_dir: str | None = str(DEFAULT_EMBEDDING_CACHE_DIR),
        local_files_only: bool = True,
    ) -> None:
        self._model_name = model_name
        self._cache_dir = cache_dir
        self._local_files_only = local_files_only
        self._inner: FastEmbedEmbedder | None = None
        self._lock = threading.Lock()

    def _ensure(self) -> FastEmbedEmbedder:
        with self._lock:
            if self._inner is None:
                self._inner = FastEmbedEmbedder(
                    self._model_name,
                    cache_dir=self._cache_dir,
                    local_files_only=self._local_files_only,
                )
            return self._inner

    def embed_documents(self, texts: Sequence[str]) -> list[FloatVector]:
        return self._ensure().embed_documents(texts)

    def embed_query(self, text: str) -> FloatVector:
        return self._ensure().embed_query(text)
