import pandas as pd
from tqdm import tqdm


# Path to the .tskv file
tskv_file_path = "data/geo-reviews-dataset-2023.tskv"

# Output Parquet file path
parquet_file_path = "data/geo-reviews-dataset-2023.parquet"


# Function to parse a single .tskv line into a dictionary
def parse_tskv_line(line):
    tokens = line.strip().split("\t")
    data = {}
    for token in tokens:
        if "=" in token:
            key, value = token.split("=", 1)
            data[key] = value.replace(
                "\\n", "\n"
            )  # Replace escaped newlines with actual newlines
    return data


def create_parquet(tskv_path, parquet_path):
    # First, count the number of lines for tqdm
    with open(tskv_path, "r", encoding="utf-8") as f:
        total_lines = sum(1 for _ in f)

    parsed_data = []
    with open(tskv_path, "r", encoding="utf-8") as file:
        for line in tqdm(file, total=total_lines, desc="Parsing .tskv file"):
            parsed_data.append(parse_tskv_line(line))

    df = pd.DataFrame(parsed_data)
    df.to_parquet(parquet_path, index=False)
    print(f"Parquet file created at '{parquet_path}' with {len(df)} records.")


if __name__ == "__main__":
    create_parquet(tskv_file_path, parquet_file_path)
