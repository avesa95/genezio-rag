import logging
import os

from dotenv import load_dotenv
from fastembed import SparseTextEmbedding, TextEmbedding
from qdrant_client import QdrantClient, models

# Load environment variables
load_dotenv()
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_HOST = os.getenv("QDRANT_HOST")
collection_name = "genezio"

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HybridSearch:
    """
    class for performing hybrid search using dense and sparse embeddings.
    """

    def __init__(self) -> None:
        """
        Initialize the Hybrid_search object with dense and sparse embedding models and a Qdrant client.
        """
        self.embedding_model = TextEmbedding(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        self.sparse_embedding_model = SparseTextEmbedding(
            model_name="Qdrant/bm42-all-minilm-l6-v2-attentions"
        )
        self.qdrant_client = QdrantClient(
            url=QDRANT_HOST, api_key=QDRANT_API_KEY, timeout=30
        )

    def query_hybrid_search(self, query, metadata_filter=None, limit=5):
        # Embed the query using the dense embedding model
        dense_query = list(self.embedding_model.embed([query]))[0].tolist()

        # Embed the query using the sparse embedding model
        sparse_query = list(self.sparse_embedding_model.embed([query]))[0]

        results = self.qdrant_client.query_points(
            collection_name=collection_name,
            prefetch=[
                models.Prefetch(
                    query=models.SparseVector(
                        indices=sparse_query.indices.tolist(),
                        values=sparse_query.values.tolist(),
                    ),
                    using="sparse",
                    limit=limit,
                ),
                models.Prefetch(
                    query=dense_query,
                    using="dense",
                    limit=limit,
                ),
            ],
            query_filter=metadata_filter,
            query=models.FusionQuery(fusion=models.Fusion.RRF),
        )

        # Extract the document number, score, and text from the payload of each scored point
        documents = [point.payload["text"] for point in results.points]

        return documents
