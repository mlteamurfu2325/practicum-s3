import pandas as pd
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import torch


# Paths
INPUT_PARQUET = "geo-reviews-dataset-2023-updated.parquet"
OUTPUT_PARQUET = "geo-reviews-enriched.parquet"

# Configuration
BATCH_SIZE = 64  # Adjust based on GPU memory
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def add_embeddings(input_path, output_path, batch_size, device):
    # Load data
    df = pd.read_parquet(input_path)
    texts = df["text"].tolist()

    # Initialize model
    model = SentenceTransformer("sergeyzh/rubert-tiny-turbo", device=device)

    embeddings = []
    num_batches = (len(texts) + batch_size - 1) // batch_size

    with tqdm(total=num_batches, desc="Generating Embeddings") as pbar:
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            batch_embeddings = model.encode(
                batch_texts, batch_size=batch_size, show_progress_bar=False
            )
            embeddings.extend(batch_embeddings)
            pbar.update(1)

    # Assign embeddings
    df["embeddings"] = embeddings

    # Save enriched data
    df.to_parquet(output_path, index=False)
    print(f"Enriched data saved to '{output_path}'.")


if __name__ == "__main__":
    add_embeddings(INPUT_PARQUET, OUTPUT_PARQUET, BATCH_SIZE, DEVICE)
