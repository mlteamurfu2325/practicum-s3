# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.15.2
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Yandex Reviews Dataset EDA
# This notebook performs exploratory data analysis on the Yandex Reviews Dataset.

# %%
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from urllib.request import urlretrieve
from tqdm import tqdm
import os
from transformers import pipeline
from collections import Counter
import numpy as np

# Set plotly theme to white
import plotly.io as pio
pio.templates.default = "plotly_white"

# %% [markdown]
# ## 1. Data Loading
# First, let's check if the data exists and download it if necessary.

# %%
def download_with_progress(url, filename):
    """Download file with progress bar"""
    class DownloadProgressBar(tqdm):
        def update_to(self, b=1, bsize=1, tsize=None):
            if tsize is not None:
                self.total = tsize
            self.update(b * bsize - self.n)
            
    with DownloadProgressBar(unit='B', unit_scale=True, miniters=1, desc=filename) as t:
        urlretrieve(url, filename, reporthook=t.update_to)

# Check if data exists
data_path = '../data/geo-reviews-dataset-2023.tskv'
if not os.path.exists(data_path):
    print(f"Downloading dataset to {data_path}")
    os.makedirs('../data', exist_ok=True)
    download_with_progress(
        'https://github.com/yandex/geo-reviews-dataset-2023/raw/refs/heads/master/geo-reviews-dataset-2023.tskv',
        data_path
    )

# %% [markdown]
# ## 2. Data Loading and Initial Exploration
# Let's load the data and look at the first few rows.

# %%
# Load the TSKV file
def parse_tskv_line(line):
    """Parse a single TSKV line into a dictionary"""
    return dict(item.split('=', 1) for item in line.strip().split('\t'))

# Count total lines for progress bar
total_lines = sum(1 for _ in open(data_path, 'r', encoding='utf-8'))

# Read the file line by line and parse TSKV format with progress bar
records = []
with open(data_path, 'r', encoding='utf-8') as f:
    for line in tqdm(f, total=total_lines, desc="Loading TSKV file"):
        try:
            records.append(parse_tskv_line(line))
        except Exception as e:
            print(f"Error parsing line: {e}")
            continue

# Convert to DataFrame
df = pd.DataFrame.from_records(records)

# Convert rating to numeric
df['rating'] = pd.to_numeric(df['rating'], errors='coerce')

print("Dataset shape:", df.shape)
print("\nColumns:", df.columns.tolist())

# Check missing values
print("\nMissing values:")
print(df.isnull().sum())

# Check data types
print("\nData types:")
print(df.dtypes)

print("\nSample data:")
df.head()

# %% [markdown]
# ## 3. Text Length Distribution Analysis

# %%
# Calculate text lengths for non-null texts
df['text_length'] = df['text'].fillna('').str.len()

# Create histogram with log scale for better visualization
fig = px.histogram(
    df[df['text_length'] > 0],  # Exclude empty reviews
    x='text_length',
    title='Distribution of Review Text Lengths',
    labels={'text_length': 'Text Length (characters)', 'count': 'Number of Reviews'},
    nbins=50,
    log_y=True  # Use log scale for better visualization of distribution
)
fig.show()

# Show text statistics
print("Text Statistics:")
print(f"Total reviews: {len(df)}")
print(f"Reviews with text: {(df['text_length'] > 0).sum()}")
print(f"Empty reviews: {(df['text_length'] == 0).sum()}")
print("\nLength statistics for non-empty reviews:")
print(df[df['text_length'] > 0]['text_length'].describe())

# %% [markdown]
# ## 4. Rubrics Distribution Analysis

# %%
# Analyze rubrics distribution
print("Rubrics Analysis:")
print(f"Reviews with rubrics: {df['rubrics'].notna().sum()}")
print(f"Reviews without rubrics: {df['rubrics'].isna().sum()}")

# Split rubrics and create a list of all rubrics
all_rubrics = []
reviews_with_multiple_rubrics = 0
for rubrics in df['rubrics'].dropna():
    rubrics_list = [r.strip() for r in rubrics.split(';') if r.strip()]
    if len(rubrics_list) > 1:
        reviews_with_multiple_rubrics += 1
    all_rubrics.extend(rubrics_list)

rubric_counts = Counter(all_rubrics)

# Create DataFrame with percentages
total_reviews_with_rubrics = df['rubrics'].notna().sum()
top_rubrics = pd.DataFrame({
    'count': pd.Series(rubric_counts),
    'percentage': pd.Series(rubric_counts) / total_reviews_with_rubrics * 100
}).sort_values('count', ascending=False).head(20)

# Create bar plot with percentages
fig = px.bar(
    top_rubrics,
    y=top_rubrics.index,
    x='percentage',
    title='Top 20 Rubrics Distribution (% of Reviews with Rubrics)',
    labels={'index': 'Rubric', 'percentage': 'Percentage of Reviews'},
    text='count'  # Show absolute counts on bars
)
fig.update_traces(textposition='auto')
fig.update_layout(yaxis={'categoryorder': 'total ascending'})
fig.show()

# Show detailed statistics
print("\nRubrics Statistics:")
print(f"Total unique rubrics: {len(rubric_counts)}")
print(f"Average rubrics per review: {len(all_rubrics) / total_reviews_with_rubrics:.2f}")
print(f"Reviews with multiple rubrics: {reviews_with_multiple_rubrics} ({reviews_with_multiple_rubrics/total_reviews_with_rubrics*100:.1f}%)")

# Distribution of number of rubrics per review
rubrics_per_review = df['rubrics'].dropna().str.split(';').apply(lambda x: len([r for r in x if r.strip()]))
print("\nNumber of rubrics per review distribution:")
print(rubrics_per_review.value_counts().sort_index())

# %% [markdown]
# ## 5. Sentiment Analysis

# %%
# Initialize sentiment analyzer
sentiment_analyzer = pipeline(model="seara/rubert-tiny2-russian-sentiment")

# Function to get sentiment with debugging
def get_sentiment(text):
    try:
        result = sentiment_analyzer(text)[0]
        # Print first few results to debug
        if len(df_sample) < 5:  # Only for first few records
            print(f"\nText: {text[:100]}...")  # First 100 chars
            print(f"Raw result: {result}")
            print(f"Score: {result['score']:.3f}")
        return result['label']
    except Exception as e:
        print(f"Error in sentiment analysis: {e}")
        return 'neutral'  # Default to neutral on error

# Apply sentiment analysis to a sample of reviews
df_with_text = df[df['text_length'] > 0]
sample_size = min(1000, len(df_with_text))  # Analyze up to 1000 reviews
print(f"Analyzing sentiment for {sample_size} reviews...")
df_sample = df_with_text.head(sample_size).copy()
tqdm.pandas(desc="Analyzing sentiments")
df_sample['sentiment'] = df_sample['text'].progress_apply(get_sentiment)

# Map sentiment labels to Russian labels for visualization
sentiment_map = {
    'neutral': 'нейтральный',
    'positive': 'позитивный',
    'negative': 'негативный'
}
df_sample['sentiment_label'] = df_sample['sentiment'].map(sentiment_map)

# Print sentiment distribution
print("\nSentiment Distribution:")
print(df_sample['sentiment'].value_counts())

# Create pie chart for sentiment distribution
fig = px.pie(
    df_sample,
    names='sentiment_label',
    title='Distribution of Review Sentiments',
    color_discrete_map={
        'нейтральный': '#808080',  # Gray for neutral
        'позитивный': '#2ecc71',   # Green for positive
        'негативный': '#e74c3c'    # Red for negative
    }
)
fig.show()

# Analyze correlation between sentiment and rating
sentiment_rating_corr = df_sample.groupby('sentiment_label')['rating'].agg(['mean', 'count']).round(2)
print("\nAverage Rating by Sentiment:")
print(sentiment_rating_corr)

# Create box plot of ratings by sentiment
fig = px.box(
    df_sample,
    x='sentiment_label',
    y='rating',
    title='Rating Distribution by Sentiment',
    labels={'sentiment_label': 'Тональность', 'rating': 'Оценка'},
    category_orders={'sentiment_label': ['нейтральный', 'позитивный', 'негативный']},
    color='sentiment_label',
    color_discrete_map={
        'нейтральный': '#808080',
        'позитивный': '#2ecc71',
        'негативный': '#e74c3c'
    }
)
fig.show()

# %% [markdown]
# ## 6. Rating Distribution Analysis

# %%
# Create bar plot of ratings
fig = px.histogram(
    df.dropna(subset=['rating']),
    x='rating',
    title='Distribution of Ratings',
    labels={'rating': 'Rating', 'count': 'Number of Reviews'},
    nbins=5,
    category_orders={'rating': [1, 2, 3, 4, 5]}  # Force integer ratings
)
fig.update_traces(xbins=dict(size=1))  # Set bin size to 1 for discrete ratings
fig.show()

# Show summary statistics
df['rating'].describe()

# %% [markdown]
# ## 7. First-level Location Analysis

# %%
# Location Analysis
print("Location Analysis:")
print(f"Reviews with address: {df['address'].notna().sum()}")
print(f"Reviews without address: {df['address'].isna().sum()}")

# Extract and clean first level location
df['first_level_location'] = df['address'].fillna('Unknown').str.split(',').str[0].str.strip()

# Calculate location statistics
total_reviews_with_location = df['address'].notna().sum()
location_stats = df['first_level_location'].value_counts()
top_locations = pd.DataFrame({
    'count': location_stats,
    'percentage': location_stats / total_reviews_with_location * 100
}).head(20)

# Create bar plot with percentages
fig = px.bar(
    top_locations,
    y=top_locations.index,
    x='percentage',
    title='Top 20 Locations Distribution (% of Reviews with Location)',
    labels={'index': 'Location', 'percentage': 'Percentage of Reviews'},
    text='count'  # Show absolute counts on bars
)
fig.update_traces(textposition='auto')
fig.update_layout(yaxis={'categoryorder': 'total ascending'})
fig.show()

# Show detailed statistics
print("\nLocation Statistics:")
print(f"Total unique locations: {len(location_stats)}")
print(f"\nTop 10 locations with review counts and percentages:")
print(top_locations[['count', 'percentage']].round(2).head(10))

# Analyze address complexity
address_parts = df['address'].dropna().str.split(',').apply(len)
print("\nAddress complexity (number of parts in address):")
print(address_parts.value_counts().sort_index())
