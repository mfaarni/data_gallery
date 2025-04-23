import streamlit as st
import numpy as np
import pandas as pd
import requests
import json
import os
import plotly.express as px
from streamlit_plotly_events import plotly_events
import altair as alt

st.markdown("""
    <style>
        /* Background color */
        .stApp {
            background-color: beige;
            color: #222;
        }

        /* Optional: Adjust the chart container */
        .element-container {
            padding: 1rem;
            background-color: black;
            border-radius: 10px;
            box-shadow: 0px 2px 10px rgba(0,0,0,0.1);
        }

        /* Titles and headers */
        h1, h2, h3 {
            color: #1a1a1a;
        }
    </style>
""", unsafe_allow_html=True)


def search(params):
    API_KEY = os.environ.get('API_KEY')
    url = "https://www.kansallisgalleria.fi/api/v1/search"
    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json"
    }
    response = requests.post(url,
                             json=params, 
                             headers=headers)
    response.raise_for_status()
    return response.json()

def fetch_data():
    with open("objects.json", "r", encoding="utf-8") as file:
        data = json.load(file)  

    df = pd.DataFrame(data)
    print(df.head())
    return df

def get_date_counts(df):
    year_data = df["yearFrom"].dropna()
    year_data = year_data.astype(int)
    counts = year_data.value_counts().sort_index()

    return pd.DataFrame({
        "year": counts.index,
        "count": counts.values
    })


def get_name_counts(df):    
    # Extract family names from the 'people' field (which is a list of dictionaries)
    df['familyName'] = df['people'].apply(lambda people: people[0]['familyName'] if isinstance(people, list) and len(people) > 0 else None)
    
    # Count occurrences of each family name
    name_counts = df['familyName'].value_counts().reset_index()
    name_counts.columns = ['familyName', 'count']
    top_artists = name_counts.head(10)
    
    return top_artists



data = fetch_data()


category_chart_data = get_name_counts(data)
chart_data = get_date_counts(data)



line_chart = alt.Chart(chart_data).mark_line(point=True).encode(
    x=alt.X("year:O", title="Year"),
    y=alt.Y("count:Q", title="Number of Pieces"),
    tooltip=["year", "count"]
).properties(
    title="Number of Art Collection Items by Year"
).interactive()

st.altair_chart(line_chart, use_container_width=True)

fig = px.bar(category_chart_data, x="familyName", y="count", title="Count by Name")
st.plotly_chart(fig)

