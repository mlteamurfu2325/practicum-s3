from sqlalchemy import create_engine, text
import streamlit as st


def get_db_connection():
    DB_HOST = 'localhost'
    DB_PORT = '5432'
    DB_NAME = 'postgres'
    DB_USER = 'postgres'
    DB_PASSWORD = 'password'

    connection_string = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    engine = create_engine(connection_string)
    return engine

@st.cache_data(ttl=360000)
def get_unique_rubrics():
    engine = get_db_connection()
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT rubric_name FROM rubrics ORDER BY rubric_name")
        )
        return [row[0] for row in result]

def get_relevant_reviews(rubric: str, rating: int, limit: int = 10):
    engine = get_db_connection()
    with engine.connect() as conn:
        # Try exact rating match first
        exact_match_query = text("""
            SELECT DISTINCT r.text, r.rating
            FROM yareviews r
            JOIN review_rubrics rr ON r.review_id = rr.review_id
            JOIN rubrics rb ON rr.rubric_id = rb.rubric_id
            WHERE rb.rubric_name = :rubric
            AND r.rating = :rating
            ORDER BY RANDOM()
            LIMIT :limit
        """)

        result = conn.execute(
            exact_match_query,
            {"rubric": rubric, "rating": rating, "limit": limit}
        )
        exact_matches = result.fetchall()

        if exact_matches:
            return ([row[0] for row in exact_matches], True)

        # If no exact matches, get random reviews from same rubric
        random_query = text("""
            SELECT DISTINCT r.text, r.rating
            FROM yareviews r
            JOIN review_rubrics rr ON r.review_id = rr.review_id
            JOIN rubrics rb ON rr.rubric_id = rb.rubric_id
            WHERE rb.rubric_name = :rubric
            ORDER BY RANDOM()
            LIMIT :limit
        """)

        result = conn.execute(
            random_query,
            {"rubric": rubric, "limit": limit}
        )
        return ([row[0] for row in result.fetchall()], False)
