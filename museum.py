import streamlit as st
import numpy as np
import pandas as pd
import requests
import json
import os


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

data = fetch_data()

print(get_date_counts(data))

chart_data = get_date_counts(data)
st.line_chart(chart_data.set_index("year"))
