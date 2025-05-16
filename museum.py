import streamlit as st
import pandas as pd
import requests
import json
import os
import plotly.express as px
import altair as alt
import random
from itertools import chain

st.set_page_config(layout="wide")


def search(params):
    API_KEY = os.getenv("API_KEY")
    response = requests.post(
        "https://www.kansallisgalleria.fi/api/v1/search",
        headers={"x-api-key": API_KEY, "Content-Type": "application/json"},
        json=params
    )
    response.raise_for_status()
    return response.json()


@st.cache_data
def load_data():
    with open("objects.json", encoding="utf-8") as f:
        return pd.DataFrame(json.load(f))


def extract_artist_names(df, top_n=16):
    def get_full_name(people):
        if isinstance(people, list) and people:
            try:
                return ", ".join([
                    f"{p.get('firstName', '').strip()} {p.get('familyName', '').strip()}"
                    for p in people if p.get('firstName') or p.get('familyName')
                ])
            
            except:
                return "Unknown"
    name_counts = (
        df['people']
        .apply(get_full_name)
        .value_counts()
        .head(top_n)
        .reset_index()
        )
    name_counts.columns = ["artistName", "count"]
    return name_counts


def extract_images(df, max_images=100):
    urls = df['multimedia'].apply(
        lambda m: m[0]['jpg']['1000'] if isinstance(m, list) and m and 'jpg' in m[0] and '1000' in m[0]['jpg'] else None
    ).dropna().tolist()
    return random.sample(urls, min(len(urls), max_images))


def extract_keywords(df, top_n=15):
    def get_keywords(keywords):
        return [k.get("en") for k in keywords if "en" in k] if isinstance(keywords, list) else []

    all_keywords = chain.from_iterable(df['keywords'].apply(get_keywords))
    return (
        pd.Series(all_keywords)
        .value_counts()
        .head(top_n)
        .reset_index()
        .rename(columns={"index": "keyword", 0: "count"})
    )


def extract_year_data(df):

    year_counts = (
        df['yearFrom']
        .dropna()
        .astype(int)
        .value_counts()
        .sort_index()
        .reset_index()
    )
    year_counts.columns = ["year", "count"]
    return year_counts


with st.spinner("Loading data..."):
    df = load_data()

st.sidebar.title("Filters")
orgs = sorted(df['responsibleOrganisation'].dropna().unique().tolist())
orgs = [o for o in orgs if o != "kuva: Kansallisgalleria / Hannu Pakarinen"]

selected_orgs = [org for org in orgs if st.sidebar.checkbox(org, value=True)]
filtered_df = df[df['responsibleOrganisation'].isin(selected_orgs)]


images = extract_images(filtered_df)
artist_name_data = extract_artist_names(filtered_df)
keyword_data = extract_keywords(filtered_df)
year_data = extract_year_data(filtered_df)


tab1, tab2 = st.tabs(["Overview", "Search"])

page_bg_img = '''<style>
body {
  position: relative;
  margin: 0;
  padding: 0;
  min-height: 100vh;
  background-image: url("https://d3uvo7vkyyb63c.cloudfront.net/1/webp/1000/2494119.jpg");
  background-size: cover;
  background-position: center;
}

body::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(50, 69, 40, 0.90); /* semi-transparent black */
  z-index: -1;
}
</style>

'''

st.markdown(page_bg_img, unsafe_allow_html=True)

with tab1:

    st.title("MuseumData")
    st.subheader("Data about Finnish museums")

    col1, col2, col3 = st.columns([1, 5, 1])

    with col1:
        for img in images[:10]:
            st.image(img)

    with col2:
        st.write("Number of Art Collection Items by Year")

        if not year_data.empty:
            year_min, year_max = year_data["year"].min(), year_data["year"].max()
            selected_range = st.slider("Select Year Range", year_min, year_max, (year_min + 400, year_max - 300), step=1)

            year_filtered = year_data[
                (year_data["year"] >= selected_range[0]) &
                (year_data["year"] <= selected_range[1])
            ]

            st.altair_chart(
                alt.Chart(year_filtered).mark_line(point=True, color="#F0A202").encode(
                    x=alt.X("year:O", title="Year"),
                    y=alt.Y("count:Q", title="Number of Pieces"),
                    tooltip=["year", "count"]
                ).interactive(),
                use_container_width=True
            )

        st.plotly_chart(
            px.bar(artist_name_data, x="artistName", y="count", title="Top Artists", color_discrete_sequence=["#F0A202"])
        )

        st.plotly_chart(
            px.scatter(keyword_data, x="keyword", y="count", size="count", color="keyword",
                    title="Most Common Keywords", size_max=60, height=500)
            .update_traces(marker=dict(line=dict(width=2, color='DarkSlateGrey')))
        )

    with col3:
        for img in images[10:20]:
            st.image(img)

with tab2:
    st.title("Search Artworks")

    search_title = st.text_input("Search by Title", "")
    search_artist = st.text_input("Search by Artist Name", "")

    def get_full_name(people):
        if isinstance(people, list) and people:
            try:
                return ", ".join([
                    f"{p.get('firstName', '').strip()} {p.get('familyName', '').strip()}"
                    for p in people if p.get('firstName') or p.get('familyName')
                ])
            
            except:
                return "Unknown"

    def get_titles(title_field):
        if isinstance(title_field, dict):
            return "\n".join([
                f"{'en: ' if lang=='en' else 'fi: ' if lang=='fi' else 'sw: '} *{txt}*"
                for lang, txt in title_field.items() if txt.strip()
            ])
        elif isinstance(title_field, list):
            # Handle case where title is a list of dicts
            return "\n".join([
                f"{'en: ' if lang=='en' else 'fi' if lang=='fi' else 'swe'} *{txt}*"
                for title_dict in title_field
                for lang, txt in title_dict.items() if txt.strip()
            ])
        return "Untitled"

    def matches(row):
        title_text = json.dumps(row.get("title", "")).lower()
        artist_names = get_full_name(row.get("people", [])).lower()
        return (
            (search_title.lower() in title_text if search_title else True) and
            (search_artist.lower() in artist_names if search_artist else True)
        )

    if search_title or search_artist:
        results_df = filtered_df[filtered_df.apply(matches, axis=1)].head(30)
        st.success(f"Showing the {len(results_df)} first items.")
    else:
        results_df = pd.DataFrame()
        st.info("Enter a title or artist name and press enter to search")

    if not results_df.empty:
        for _, row in results_df.iterrows():
            col1, col2 = st.columns([1, 4])
            with col1:
                image_url = row['multimedia'][0]['jpg']['1000'] if isinstance(row['multimedia'], list) and row['multimedia'] and 'jpg' in row['multimedia'][0] else None
                if image_url:
                    # Title as caption (optional), image expands on click
                    st.image(image_url, use_column_width=True, caption=None)

                    # Title and Artist below image
                    piece_titles = get_titles(row.get('title', {}))
                    artist_full_name = get_full_name(row.get('people'))
                    st.markdown(f"**Title:** {piece_titles}")
                    st.markdown(f"**Artist:** {artist_full_name}")

            with col2:
                st.markdown(f"### {get_titles(row.get('title', {}))}")
                st.markdown(f"**Artist(s):** {get_full_name(row.get('people'))}")
                try:
                    st.markdown(f"**Year:** {int(row.get('yearFrom'))}")
                except:
                    st.markdown("Year: unknown") 
                st.markdown("---")