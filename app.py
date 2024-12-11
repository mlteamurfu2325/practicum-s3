import streamlit as st
from src.llm import ReviewGenerator


# Initialize ReviewGenerator in session state if not exists
if 'review_generator' not in st.session_state:
    st.session_state.review_generator = ReviewGenerator()

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
    .stApp {
        background-color: #0e1117;
    }

    .card {
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
    h1, h2, h3 {
        color: #fafafa;
        margin-bottom: 1.5rem;
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
        placeholder="Например: качество обслуживания"
    )

    st.markdown('<p class="big-font">Рубрика:</p>', unsafe_allow_html=True)
    category = st.text_input(
        "Рубрика",
        key="category",
        label_visibility="collapsed",
        placeholder="Например: ресторан, кафе, магазин"
    )

with col2:
    st.markdown('<p class="big-font">Рейтинг:</p>', unsafe_allow_html=True)
    rating = st.number_input(
        "Рейтинг",
        min_value=1,
        max_value=5,
        value=4,
        key="rating",
        label_visibility="collapsed"
    )
    # Display stars based on rating
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
        with st.spinner("Генерируем отзыв..."):
            review, error = st.session_state.review_generator.generate_review(
                theme=theme,
                rating=rating,
                category=category
            )

        if error:
            st.error(error)
        else:
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
            st.markdown('</div>', unsafe_allow_html=True)
