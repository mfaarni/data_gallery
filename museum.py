import streamlit as st
import numpy as np
import pandas as pd
import requests
import json
import os
import plotly.express as px
from streamlit_plotly_events import plotly_events
from itertools import chain
import altair as alt
import random


st.set_page_config(layout="wide") 

def search(params):
    API_KEY = os.environ.get('API_KEY')
    url = "https://www.kansallisgalleria.fi/api/v1/search"
    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json"
    }
    response = requests.post(url, json=params, headers=headers)
    response.raise_for_status()
    return response.json()

def fetch_data():
    with open("objects.json", "r", encoding="utf-8") as file:
        data = json.load(file)  
    return pd.DataFrame(data)

def get_date_counts(df):
    year_data = df["yearFrom"].dropna().astype(int)
    counts = year_data.value_counts().sort_index()
    return pd.DataFrame({
        "year": counts.index,
        "count": counts.values
    })

def get_name_counts(df):    
    df = df.copy()
    df['familyName'] = df['people'].apply(lambda people: people[0]['familyName'] if isinstance(people, list) and len(people) > 0 else None)
    name_counts = df['familyName'].value_counts().reset_index()
    name_counts.columns = ['familyName', 'count']
    return name_counts.head(10)

def get_images(df, max_images=100):
    df = df.copy()
    df['jpg'] = df['multimedia'].apply(lambda m: m[0]['jpg']['1000'] if isinstance(m, list) and m and 'jpg' in m[0] and '1000' in m[0]['jpg'] else None)
    
    valid_images = df['jpg'].dropna().tolist()
    if not valid_images:
        return []
    
    # Pick random sample safely
    sample_size = min(len(valid_images), max_images)
    return random.sample(valid_images, sample_size)


def get_keywords_data(df):
    df = df.copy()
    
    def extract_keywords(keywords):
        if isinstance(keywords, list):
            return [k.get("en") for k in keywords if "en" in k]
        return []

    df['keywords_en'] = df['keywords'].apply(extract_keywords)
    
    # Use itertools.chain for fast flattening
    all_keywords = list(chain.from_iterable(df['keywords_en']))
    
    keyword_counts = pd.Series(all_keywords).value_counts().reset_index()
    keyword_counts.columns = ['keyword', 'count']
    return keyword_counts.head(15)

# === Main ===

with st.empty():

    st.write("Fetching data...")
    data = fetch_data()

    # Sidebar: filter by responsible organisation
    st.sidebar.title("Filters")
    orgs = sorted(data['responsibleOrganisation'].dropna().unique())
    orgs.remove("kuva: Kansallisgalleria / Hannu Pakarinen")
    selected_orgs = [org for org in orgs if st.sidebar.checkbox(org, value=True)]
    st.write(f"Selected orgs: {selected_orgs}")

    filtered_data = data[data['responsibleOrganisation'].isin(selected_orgs)].copy()

    st.write("Generating category chart...")
    category_chart_data = get_name_counts(filtered_data)
    st.write("Getting date counts...")
    chart_data = get_date_counts(filtered_data)
    st.write("Getting images...")
    images = get_images(filtered_data)
    st.write("Generating keywords...")
    keyword_data = get_keywords_data(filtered_data)
    st.write("Finished data processing")
    st.empty()

# Line chart
line_chart = alt.Chart(chart_data).mark_line(
    color="#F0A202", 
    point=alt.OverlayMarkDef(color="#F0A202")
).encode(
    x=alt.X("year:O", title="Year"),
    y=alt.Y("count:Q", title="Number of Pieces"),
    tooltip=["year", "count"]
).properties(
    title="Number of Art Collection Items by Year"
).interactive()

# Layout
st.title("MuseumData")
st.subheader("Data about Finnish museums.")
st.markdown('##')
col1, col2, col3 = st.columns([1, 5, 1])

with col1:
    for i in range(min(10, len(images))):
        st.image(images[i])

with col2:
    st.altair_chart(line_chart, use_container_width=True, theme="streamlit")
    fig = px.bar(category_chart_data, x="familyName", y="count", title="Top Artists",
                 color_discrete_sequence=["#F0A202"])
    st.plotly_chart(fig)

    # Bubble chart for keywords
    bubble_fig = px.scatter(keyword_data, x="keyword", y="count", size="count",
                            color="keyword", title="Most Common Keywords",
                            size_max=60, height=500)
    bubble_fig.update_traces(marker=dict(line=dict(width=2, color='DarkSlateGrey')))
    st.plotly_chart(bubble_fig)

with col3:
    for i in range(10, min(20, len(images))):
        st.image(images[i])
