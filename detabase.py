from deta import Deta
import streamlit as st

DETA_KEY=st.secrets.db_credentials.detakey

deta = Deta(DETA_KEY)

db = deta.Base("location_db")

def insert_location(key, locality, suburb, country, latitude, longitude, category, rating, period, comment, image):
    return db.put({"key": key, "locality": locality, "suburb": suburb, "country": country, "latitude": latitude, "longitude": longitude, "category": category, "rating": rating, "period": period, "comment": comment, "image": image})

def fetch_all_data():
    res = db.fetch()
    return res.items

def get_period(period):
    return db.get(period)

