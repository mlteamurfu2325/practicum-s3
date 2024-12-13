import streamlit as st
from src.llm import ReviewGenerator
from src.db.db_connection import get_unique_rubrics, get_relevant_reviews


# Initialize ReviewGenerator in session state if not exists
if 'review_generator' not in st.session_state:
    st.session_state.review_generator = ReviewGenerator()


def generate_review(theme, rating, category, reviews):
    """Helper function to generate review with spinner"""
    with st.spinner("Генерируем отзыв..."):
        reviews_text = "\n\n".join(
            f"Пример {i+1}:\n{review}" 
            for i, review in enumerate(reviews)
        )

        review, error = st.session_state.review_generator.generate_review(
            theme=theme,
            rating=rating,
            category=category,
            real_reviews=reviews_text
        )

        if error:
            st.error(error)
            return

        st.markdown(
            '<div class="card">'
            '<h2>🏁 Ваш отзыв готов!</h2>',
            unsafe_allow_html=True
        )
        st.text_area(
            "Сгенерированный отзыв",
            review,
            height=200,
            label_visibility="collapsed"
        )

        expander_text = (
            "📚 Показать реальные отзывы, использованные для вдохновения"
        )
        with st.expander(expander_text, expanded=False):
            for i, review in enumerate(reviews, 1):
                st.markdown(f"**Отзыв {i}:**")
                st.text(review)
                st.markdown("---")

        st.markdown('</div>', unsafe_allow_html=True)


# Page configuration
st.set_page_config(
    page_title="Генератор отзывов Яндекс.Карты",
    page_icon="🤖",
    layout="wide"
)

# Custom CSS for styling
st.markdown("""
    <style>
    /* Main container styling */
    .main {
        padding: 2rem;
    }

    /* Card styling */
        background-color: #1e2227;
        padding: 2rem;
        border-radius: 10px;
        border: 1px solid #2e3238;
        margin-bottom: 2rem;
    }

    /* Input styling */
    .stTextInput > div > div > input {
        background-color: #262730;
        border: 1px solid #3e4247;
        padding: 1rem;
        font-size: 1rem;
        border-radius: 8px;
    }

    .stNumberInput > div > div > input {
        background-color: #262730;
        border: 1px solid #3e4247;
        padding: 1rem;
        font-size: 1rem;
        border-radius: 8px;
    }

    /* Button styling */
    .stButton > button {
        width: 100%;
        padding: 0.75rem 1.5rem;
        font-size: 1.2rem;
        font-weight: 600;
        color: white;
        background: linear-gradient(45deg, #FF4B2B, #FF416C);
        border: none;
        border-radius: 8px;
        cursor: pointer;
        transition: transform 0.2s;
    }

    .stButton > button:hover {
        transform: translateY(-2px);
    }

    /* Text area styling */
    .stTextArea > div > div > textarea {
        background-color: #262730;
        border: 1px solid #3e4247;
        padding: 1rem;
        font-size: 1rem;
        border-radius: 8px;
        color: #fafafa;
    }

    /* Headers styling */
    h1 {
        color: #fafafa;
        margin-bottom: 1.5rem;
        font-size: 1.5rem !important;
    }

    h2 {
        color: #fafafa;
        margin-bottom: 1.5rem;
        font-size: 1.2rem !important;
    }

    .big-font {
        color: #fafafa;
        font-size: 1.2rem !important;
        margin-bottom: 0.5rem;
        font-weight: 500;
    }

    /* Error message styling */
    .stAlert {
        background-color: #3e1c1c;
        border: 1px solid #ff4b4b;
        color: #ff4b4b;
        padding: 1rem;
        border-radius: 8px;
    }

    /* Warning message styling */
    .stWarning {
        background-color: #3e351c;
        border: 1px solid #ffd700;
        color: #ffd700;
        padding: 1rem;
        border-radius: 8px;
    }

    /* Loading spinner styling */
    .stSpinner > div {
        border-color: #FF4B2B !important;
    }

    /* Expander styling */
    .streamlit-expanderHeader {
        font-size: 1.3rem !important;
        font-weight: 500;
    }
    </style>
""", unsafe_allow_html=True)

# Title with emojis
st.markdown(
    '<div class="card">'
    '<h1 style="text-align: center; margin-bottom: 0.5rem;">'
    '🤖 ✏️ 👀 Генератор отзывов по мотивам Яндекс Карт'
    '</h1>'
    '</div>',
    unsafe_allow_html=True
)

# Parameters section
st.markdown(
    '<div class="card">'
    '<h2>🔍 Выберите параметры желаемого отзыва:</h2>',
    unsafe_allow_html=True
)

# Input fields with larger labels
col1, col2 = st.columns([3, 1])

with col1:
    st.markdown(
        '<p class="big-font">Ключевая тема отзыва:</p>',
        unsafe_allow_html=True
    )
    theme = st.text_input(
        "Ключевая тема отзыва",
        key="theme",
        label_visibility="collapsed",
        placeholder="Например: качество обслуживания",
        value="супер цены"
    )

    st.markdown('<p class="big-font">Рубрика:</p>', unsafe_allow_html=True)
    rubrics = get_unique_rubrics()
    category = st.selectbox(
        "Рубрика",
        options=rubrics,
        key="category",
        label_visibility="collapsed"
    )

with col2:
    st.markdown('<p class="big-font">Рейтинг:</p>', unsafe_allow_html=True)
    rating = st.number_input(
        "Рейтинг",
        min_value=1,
        max_value=5,
        value=5,
        key="rating",
        label_visibility="collapsed"
    )
    st.markdown(f"{'⭐' * int(rating)}")

# Generate button with padding
st.markdown("<div style='padding: 1.5rem 0;'>", unsafe_allow_html=True)
generate = st.button("Сгенерировать!", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# Review generation section
if generate:
    if not theme or not category:
        st.error("Пожалуйста, заполните все поля!")
    else:
        reviews, exact_match = get_relevant_reviews(category, rating)

        if not reviews:
            st.error(f"В базе данных не найдено отзывов для рубрики '{category}'")
        else:
            if not exact_match:
                st.info(
                    f"Для рубрики '{category}' не найдено отзывов с рейтингом {rating}. "
                    "Будут использованы случайные отзывы из этой рубрики."
                )

            # Proceed with generation
            generate_review(theme, rating, category, reviews)
