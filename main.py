import logging
import os
import tempfile
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from qdrant_client import QdrantClient

from hybrid_retrieval import HybridSearch
from indexing import DocumentProcessor, QdrantIndexer

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_HOST = os.getenv("QDRANT_HOST")
COLLECTION_NAME = "genezio"


class DocumentStats:
    def __init__(self):
        self.client = QdrantClient(
            url=QDRANT_HOST,
            api_key=QDRANT_API_KEY,
        )
        self.hybrid_search = HybridSearch()

    def get_indexed_documents(self):
        try:
            # Get all points from Qdrant
            response = self.client.scroll(
                collection_name=COLLECTION_NAME, limit=10000, with_payload=True
            )

            points = response[0]
            documents = {}

            for point in points:
                payload = point.payload
                filename = payload.get("file_name")

                if filename not in documents:
                    documents[filename] = {
                        "pages": set(),
                        "file_path": payload.get("file_path", ""),
                        "file_type": payload.get("file_type", ""),
                        "file_size": payload.get("file_size", ""),
                        "creation_date": payload.get("creation_date", ""),
                        "last_modified_date": payload.get("last_modified_date", ""),
                        "text_chunks": [],
                    }

                # Add page number to set of pages
                if "page_label" in payload:
                    documents[filename]["pages"].add(payload["page_label"])

                # Add text chunk
                if "text" in payload:
                    documents[filename]["text_chunks"].append(
                        {
                            "page": payload.get("page_label"),
                            "text": payload["text"][:200] + "..."
                            if len(payload["text"]) > 200
                            else payload["text"],
                        }
                    )

            # Convert sets to lists for display
            for doc in documents.values():
                doc["pages"] = sorted(
                    list(doc["pages"]),
                    key=lambda x: int(x) if x.isdigit() else float("inf"),
                )

            return documents

        except Exception as e:
            logger.error(f"Error fetching documents: {e}")
            return {}

    def search_documents(self, query_text, limit=5):
        try:
            return self.hybrid_search.query_hybrid_search(query_text, limit=limit)
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []


def format_file_size(size_in_bytes):
    """Convert bytes to human readable format"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_in_bytes < 1024:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024
    return f"{size_in_bytes:.2f} TB"


def display_documents(documents):
    if not documents:
        st.info("No documents have been indexed yet.")
        return

    st.metric("Total Documents Indexed", len(documents))

    for filename, doc in documents.items():
        with st.expander(f"📄 {filename}"):
            # Create three columns for metadata
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("**File Details**")
                st.write(f"Size: {format_file_size(int(doc['file_size']))}")
                st.write(f"Type: {doc['file_type']}")
                st.write(f"Pages: {', '.join(doc['pages'])}")

            with col2:
                st.markdown("**Dates**")
                st.write(f"Created: {doc['creation_date']}")
                st.write(f"Modified: {doc['last_modified_date']}")

            with col3:
                st.markdown("**Storage**")
                st.write("Path:", doc["file_path"])

            # Show text chunks in a tabbed interface
            if doc["text_chunks"]:
                tabs = st.tabs(
                    [f"Page {chunk['page']}" for chunk in doc["text_chunks"]]
                )
                for tab, chunk in zip(tabs, doc["text_chunks"]):
                    with tab:
                        st.text_area(
                            "Content Preview",
                            chunk["text"],
                            height=150,
                            disabled=True,
                            key=f"{filename}_{chunk['page']}",
                        )


def display_search_results(results):
    if not results:
        st.info("No results found.")
        return

    for i, result in enumerate(results):
        st.markdown("**Content**")
        st.text_area(
            "Text",
            result,
            height=150,
            disabled=True,
            key=f"result_{i}",
        )


def main():
    st.set_page_config(page_title="Genezio RAG", page_icon="📚", layout="wide")

    st.title("📚 Genezio RAG")

    # Create tabs for different sections
    tab1, tab2, tab3 = st.tabs(["Upload Documents", "Indexed Documents", "Search"])

    with tab1:
        st.write("Upload your PDF documents to index them in the database.")

        # File uploader
        uploaded_files = st.file_uploader(
            "Choose PDF files", type="pdf", accept_multiple_files=True
        )

        if uploaded_files:
            st.write("Selected files:")
            for file in uploaded_files:
                st.text(f"📄 {file.name}")

            if st.button("Process and Index Documents", type="primary"):
                with st.spinner("Processing documents..."):
                    # Create temporary directory for uploaded files
                    with tempfile.TemporaryDirectory() as temp_dir:
                        # Save uploaded files
                        for uploaded_file in uploaded_files:
                            file_path = Path(temp_dir) / uploaded_file.name
                            with open(file_path, "wb") as f:
                                f.write(uploaded_file.getvalue())

                        # Process documents
                        processor = DocumentProcessor()
                        nodes, error = processor.process_documents(temp_dir)

                        if error:
                            st.error(error)
                            return

                        progress_text = st.text("Indexing documents...")

                        # Index documents
                        indexer = QdrantIndexer()
                        indexer.setup_collection(nodes[0].text)
                        success = indexer.index_documents(nodes)

                        if success:
                            st.success("✅ Documents successfully indexed!")
                        else:
                            st.error("❌ Some batches failed during indexing.")

    with tab2:
        st.write("View all documents currently indexed in the database.")

        # Add refresh button with some spacing
        col1, col2 = st.columns([1, 6])
        with col1:
            if st.button("🔄 Refresh"):
                st.session_state.refresh_stats = True

        # Get and display documents
        documents = DocumentStats().get_indexed_documents()
        display_documents(documents)

    with tab3:
        st.write("Search through indexed documents")

        # Search interface
        query = st.text_input("Enter your search query")
        num_results = st.slider("Number of results", min_value=1, max_value=20, value=5)

        if st.button("🔍 Search", type="primary"):
            if query:
                with st.spinner("Searching..."):
                    # Perform search
                    doc_stats = DocumentStats()
                    results = doc_stats.search_documents(query, limit=num_results)

                    # Display results
                    display_search_results(results)
            else:
                st.warning("Please enter a search query.")


if __name__ == "__main__":
    main()
