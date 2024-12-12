import pandas as pd
from transformers import AutoTokenizer
from tqdm import tqdm


# Path to the original Parquet file
parquet_file_path = 'geo-reviews-dataset-2023.parquet'

# Path for the updated Parquet file
updated_parquet_path = 'geo-reviews-dataset-2023-updated.parquet'

# Token limit
TOKEN_LIMIT = 2048

def check_and_truncate_tokens(parquet_path, token_limit, updated_parquet_path):
    # Load the DataFrame
    print(f"Loading Parquet file from '{parquet_path}'...")
    df = pd.read_parquet(parquet_path)

    # Initialize the tokenizer
    print("Initializing the tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained('sergeyzh/rubert-tiny-turbo')

    # Initialize tqdm for pandas apply
    tqdm.pandas(desc="Processing reviews")

    # Function to count tokens and truncate text if necessary
    def process_text(text):
        if pd.isna(text):
            return pd.Series({'tokens_num': 0, 'text': text, 'is_trunc_for_token_limit': 0})
        
        # Encode the text to get tokens
        tokens = tokenizer.encode(text, add_special_tokens=False)
        token_count = len(tokens)
        
        # Check if token count exceeds the limit
        if token_count > token_limit:
            # Truncate tokens to the limit
            truncated_tokens = tokens[:token_limit]
            # Decode back to text
            truncated_text = tokenizer.decode(truncated_tokens, clean_up_tokenization_spaces=True)
            return pd.Series({
                'tokens_num': token_count,
                'text': truncated_text,
                'is_trunc_for_token_limit': 1
            })
        else:
            return pd.Series({
                'tokens_num': token_count,
                'text': text,
                'is_trunc_for_token_limit': 0
            })

    # Apply the processing to each review's text
    print("Counting tokens and truncating texts if necessary...")
    processed = df['text'].progress_apply(process_text)
    
    # Concatenate the processed data with the original DataFrame
    df = pd.concat([df.drop(columns=['text']), processed], axis=1)
    
    # Save the updated DataFrame to the Parquet file
    df.to_parquet(updated_parquet_path, index=False)
    print(f"Updated Parquet file with 'tokens_num' and 'is_trunc_for_token_limit' columns saved to '{updated_parquet_path}'.")

    # Identify reviews that were truncated
    truncated_reviews = df[df['is_trunc_for_token_limit'] == 1]
    
    if not truncated_reviews.empty:
        print(f"\nThere are {len(truncated_reviews)} reviews that were truncated to fit within the {token_limit}-token limit.")
        print(truncated_reviews[['address', 'name_ru', 'rating', 'tokens_num']])
        
        # Save truncated reviews to a separate CSV for reference
        truncated_reviews.to_csv('truncated_reviews.csv', index=False)
        print("\nDetails of truncated reviews have been saved to 'truncated_reviews.csv'.")
    else:
        print(f"\nNo reviews exceeded the {token_limit}-token limit. No truncation was necessary.")
    
    # Optionally, identify and save reviews that still exceed the token limit (should be none)
    still_exceeds = df[df['tokens_num'] > token_limit]
    if not still_exceeds.empty:
        print(f"\nWarning: There are {len(still_exceeds)} reviews still exceeding the {token_limit}-token limit after truncation.")
        still_exceeds.to_csv('reviews_exceeding_token_limit_after_truncation.csv', index=False)
        print("Details have been saved to 'reviews_exceeding_token_limit_after_truncation.csv'.")
    else:
        print("\nAll reviews are now within the token limit after truncation.")

    # Display summary statistics
    print("\nToken Count Summary:")
    print(df['tokens_num'].describe())

if __name__ == "__main__":
    check_and_truncate_tokens(parquet_file_path, TOKEN_LIMIT, updated_parquet_path)
