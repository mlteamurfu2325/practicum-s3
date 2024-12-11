import streamlit as st


# Page configuration
st.set_page_config(
    page_title="Генератор отзывов Яндекс.Карты",
    page_icon="🤖",
    layout="wide"
)

# Custom CSS for styling
st.markdown("""
    <style>
    .big-font {
        font-size: 24px !important;
    }
    .input-container {
        margin-bottom: 20px;
    }
    .stButton>button {
        width: 200px;
        height: 50px;
        font-size: 20px;
        margin: 30px 0;
    }
    </style>
""", unsafe_allow_html=True)

# Title with emojis
st.markdown(
    "# 🤖 ✏️ 👀 Генератор отзывов по мотивам Яндекс Карт"
)

# Parameters section
st.markdown(
    "## 🔍 Выберите параметры желаемого отзыва:"
)

# Input fields with larger labels
st.markdown(
    '<p class="big-font">Ключевая тема отзыва:</p>',
    unsafe_allow_html=True
)
theme = st.text_input("", key="theme", label_visibility="collapsed")

st.markdown('<p class="big-font">Рейтинг:</p>', unsafe_allow_html=True)
rating = st.number_input(
    "",
    min_value=1,
    max_value=5,
    value=4,
    key="rating",
    label_visibility="collapsed"
)

st.markdown('<p class="big-font">Рубрика:</p>', unsafe_allow_html=True)
category = st.text_input("", key="category", label_visibility="collapsed")

# Generate button
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    generate = st.button("Сгенерировать!", use_container_width=True)

# Review generation section
if generate:
    if not theme or not category:
        st.error("Пожалуйста, заполните все поля!")
    else:
        st.markdown("## 🏁 Ваш отзыв готов!")
        mockup_review = "Здесь будет находиться текст сгенерированного отзыва"
        st.text_area(
            "",
            mockup_review,
            height=200,
            label_visibility="collapsed"
        )
