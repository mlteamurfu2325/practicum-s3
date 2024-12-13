import pandas as pd
import numpy as np
from sqlalchemy import (
    create_engine, MetaData, Table, Column, Integer, Float, Text,
    Index, text, BigInteger, String, ForeignKey, TIMESTAMP
)
from pgvector.sqlalchemy import Vector
from tqdm import tqdm
import ast
from datetime import datetime


# Database connection parameters
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'postgres'
DB_USER = 'postgres'
DB_PASSWORD = 'password'

# Connection string
connection_string = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# Create an engine and connect to the database
engine = create_engine(connection_string)
conn = engine.connect()

# Enable pgvector extension
conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

# Read the Parquet file into a DataFrame
df = pd.read_parquet('data/geo-reviews-enriched.parquet')

# Ensure the 'embeddings' column contains lists of floats
first_embedding = df['embeddings'].iloc[0]

if isinstance(first_embedding, (list, tuple, np.ndarray)):
    if isinstance(first_embedding, np.ndarray):
        df['embeddings'] = df['embeddings'].apply(lambda x: x.tolist())
elif isinstance(first_embedding, str):
    df['embeddings'] = df['embeddings'].apply(ast.literal_eval)
else:
    raise ValueError("Unsupported format for 'embeddings' column.")

# Get the dimension of the embeddings
embedding_dim = len(df['embeddings'].iloc[0])

# Define the table schemas using SQLAlchemy
metadata = MetaData()

# Main reviews table
yareviews = Table(
    'yareviews',
    metadata,
    Column('review_id', BigInteger, primary_key=True, autoincrement=True),
    Column('address', Text),
    Column('name_ru', Text),
    Column('rating', Float),
    Column('text', Text),
    Column('tokens_num', Integer),
    Column('is_trunc_for_token_limit', Integer),
    Column('embeddings', Vector(embedding_dim)),
    Column('created_at', TIMESTAMP, default=datetime.utcnow)
)

# Rubrics reference table
rubrics = Table(
    'rubrics',
    metadata,
    Column('rubric_id', Integer, primary_key=True, autoincrement=True),
    Column('rubric_name', String(255), unique=True, nullable=False)
)

# Junction table for reviews-rubrics mapping
review_rubrics = Table(
    'review_rubrics',
    metadata,
    Column('review_id', BigInteger, ForeignKey('yareviews.review_id')),
    Column('rubric_id', Integer, ForeignKey('rubrics.rubric_id')),
    Index('idx_review_rubrics_rubric_id', 'rubric_id')
)

# Create all tables
metadata.create_all(engine)

# Create vector similarity search index
with engine.begin() as connection:
    index_exists = connection.execute(
        text("SELECT to_regclass('public.yareviews_embeddings_idx');")
    ).scalar()
    if not index_exists:
        connection.execute(text(
            "CREATE INDEX yareviews_embeddings_idx "
            "ON yareviews "
            "USING ivfflat (embeddings vector_l2_ops) "
            "WITH (lists = 100);"
        ))
        connection.execute(text("ANALYZE yareviews;"))

# Extract unique rubrics from the dataset
unique_rubrics = sorted(set(
    rubric.strip()
    for row in df['rubrics'].dropna()
    for rubric in row.split(';')
))

# Insert rubrics and get mapping dictionary
with engine.begin() as connection:
    # Insert rubrics
    for rubric in unique_rubrics:
        connection.execute(
            text("INSERT INTO rubrics (rubric_name) "
                 "VALUES (:rubric) ON CONFLICT DO NOTHING"),
            {"rubric": rubric}
        )

    # Get rubrics mapping dictionary
    result = connection.execute(
        text("SELECT rubric_id, rubric_name FROM rubrics")
    )
    rubrics_dict = {row[1]: row[0] for row in result}

# Prepare reviews data
reviews_data = []
review_rubrics_data = []

for idx, row in df.iterrows():
    review_data = {
        'address': row['address'],
        'name_ru': row['name_ru'],
        'rating': row['rating'],
        'text': row['text'],
        'tokens_num': row['tokens_num'],
        'is_trunc_for_token_limit': row['is_trunc_for_token_limit'],
        'embeddings': row['embeddings'],
        'created_at': datetime.utcnow()
    }
    reviews_data.append(review_data)

# Insert reviews in batches
batch_size = 1000
total_records = len(reviews_data)

print("Inserting reviews...")
with engine.begin() as connection:
    for i in tqdm(range(0, total_records, batch_size),
                 desc='Inserting reviews', unit='batch'):
        batch = reviews_data[i:i + batch_size]
        result = connection.execute(
            yareviews.insert().returning(yareviews.c.review_id),
            batch
        )
        review_ids = [row[0] for row in result]

        # Prepare review-rubrics mappings for this batch
        for j, review_id in enumerate(review_ids):
            if pd.notna(df.iloc[i + j]['rubrics']):
                rubrics_list = [
                    r.strip() for r in df.iloc[i + j]['rubrics'].split(';')
                ]
                for rubric in rubrics_list:
                    review_rubrics_data.append({
                        'review_id': review_id,
                        'rubric_id': rubrics_dict[rubric]
                    })

# Insert review-rubrics mappings in batches
print("Inserting review-rubrics mappings...")
with engine.begin() as connection:
    for i in tqdm(range(0, len(review_rubrics_data), batch_size),
                 desc='Inserting mappings', unit='batch'):
        batch = review_rubrics_data[i:i + batch_size]
        connection.execute(review_rubrics.insert(), batch)

# Close the connection
conn.close()

print("Data import completed successfully.")
