import streamlit as st
from shapely.geometry import Point, Polygon
import geopandas as gpd
import pandas as pd
import geopy
import folium
from folium.plugins import Draw
from streamlit_folium import st_folium
from streamlit_option_menu import option_menu

from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import time
from datetime import datetime

from myfunc import get_address_by_location, get_key_from_value
import detabase as db

from PIL import Image
import io

from google.oauth2 import service_account
from google.cloud import storage

def load_image(image_file):
    img = Image.open(image_file)
    return img

# ------------ CONFIG -------------------
st.set_page_config(page_title='TMap', page_icon=None, layout="wide")

hide_table_row_index = """
    <style>
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """

st.markdown(hide_table_row_index, unsafe_allow_html=True)

# Create API client.
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
client = storage.Client(credentials=credentials)

bucket_name = st.secrets["bucket_name"]

# -------------- SIDEBAR -----------------------------
st.sidebar.title("Enter address")

# street = st.sidebar.text_input("Street", "75 Bay Street")
# city = st.sidebar.text_input("City", "Toronto")
# province = st.sidebar.text_input("Province", "Ontario")
locality = st.sidebar.text_input("Location", "Bugis")
country = st.sidebar.text_input("Country", "Singapore")

# st.write("-------------")
# width_map = st.sidebar.number_input("Map Width", 250)

# -------------- MAP -------------------------------------
geolocator = Nominatim(user_agent="GTA Lookup")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
# location = geolocator.geocode(street+", "+city+", "+province+", "+country)
location = geolocator.geocode(locality+", "+country)


lat = location.latitude
lon = location.longitude

# map_data = pd.DataFrame({'lat': [lat], 'lon': [lon]})
# st.map(map_data)

# ---------- NAV MENU ----------------
select_options = ["View Map", "New Entry"]
selected = option_menu(menu_title=None,
    options=select_options,
    icons=["bar-chart-fill", "pencil-fill"], # https://icons.getbootstrap.com
    orientation='horizontal')

# Folium
m = folium.Map(location=[lat, lon], tiles='CartoDB dark_matter', zoom_start=15) #tiles='CartoDB dark_matter'

# Getting data from DETA and create dataframe
df = pd.DataFrame(columns=['latitude', 'longitude', 'location', 'country', 'category', 'rating', 'period', 'comment', 'image'])
all_cat = ["Food", "Entertainment", "Nature"]
caticon = {all_cat[0]:'glass', all_cat[1]:'plane', all_cat[2]:'fire'}
catcol = {all_cat[0]:'red', all_cat[1]:'blue', all_cat[2]:'green'}
dataitems = db.fetch_all_data()
for item in dataitems:
    dlat = item['latitude']
    dlon = item['longitude']
    dloc = item['locality']
    dcon = item['country']
    dcat = item['category']
    drat = item['rating']
    dper = item['period']
    dcom = item['comment']
    dima = item['image']
    df.loc[len(df)] = [dlat, dlon, dloc, dcon, dcat, drat, dper, dcom, dima]
    folium.Marker(location=[dlat, dlon], popup=dloc,
        icon=folium.Icon(icon=caticon[dcat], color=catcol[dcat])).add_to(m)

if selected == select_options[0]:
    col1, col2 = st.columns([1,1])
    with col1:
        output = st_folium(m, width=350, height=450) # width=250,
        last_obj = output['last_object_clicked']
        if last_obj:
            displat = last_obj['lat']
            displon = last_obj['lng']
            dff = df[(df['latitude']==displat)&(df['longitude']==displon)]
            disploc = dff.iloc[0]['location']
            dispcon = dff.iloc[0]['country']
            dispcat = dff.iloc[0]['category']
            disprat = dff.iloc[0]['rating']
            dispper = dff.iloc[0]['period']
            dispcom = dff.iloc[0]['comment']
            dispima = dff.iloc[0]['image']
            with col2:
                st.caption(dispper+" | "+dispcat+" | "+dispcon)
                st.subheader(disploc)

                st.text(dispcom)
                # st.image(load_image(dispima),width=250)
                st.image(dispima, use_column_width='always')
    # st.write(output)
    # @st.experimental_memo(ttl=600)
    # def read_file(bucket_name, blob):
    #     # bucket = client.bucket(bucket_name)
    #     # content = bucket.blob(file_path).download_as_string().decode("utf-8")
    #     link = f'https://storage.cloud.google.com/{bucket_name}/{blob}'
    #     return link

    # bucket_name = "streamlit-map-storage"
    # file_path = "1995train.jpg"
    # blobs = client.list_blobs(bucket_name)
    # blob = [blob.name for blob in blobs][0]
    # imglink = read_file(bucket_name, blob)
    # st.image(imglink, width=800)
    # content = read_file(bucket_name, file_path)
    # st.image(load_image(content),width=250)

def upload_to_bucket(blob_name, blob_type, bytedata, bucket_name):
    """ Upload data to a google cloud bucket and get public URL"""
    # Explicitly use service account credentials by specifying the private key
    # file.
    bucket = client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(bytedata, content_type=blob_type)
    # returns a public url
    # blob.make_public()
    return f'https://storage.cloud.google.com/{bucket_name}/{blob_name}'

if selected == select_options[1]:
    # Add marker
    col1, col2 = st.columns([1,1])
    with col1:
        Draw().add_to(m) # Draw(export=True)
        output = st_folium(m, width=350, height=450) #width=725
    with col2:
        loglocality = st.text_input("Location", locality, key='loglocality')
        logcountry = st.text_input("Country", country, key='logcountry')
        if output['all_drawings']:
            drawingpoints = output['all_drawings']
            for pnt in drawingpoints:
                coord = pnt['geometry']['coordinates']
                loglon = coord[0]
                loglat = coord[1]
        category = st.selectbox("Category", all_cat, key='category')
        rating = st.selectbox("Star", (1, 2, 3, 4, 5), key='rating')
        mydate = st.date_input("Date", datetime.today(), key='mydate')
        comment = st.text_area('Comments', key='comment')
    image_file = st.file_uploader("Upload Images", type=["png","jpg","jpeg"], key='image_file')
    # image_data = image_file.read()
    if image_file is not None:
        file_details = {"filename":image_file.name, "filetype":image_file.type, "filesize":image_file.size}
        # st.write(file_details)
        st.image(load_image(image_file), width=250)

    if st.button("Submit"):
        loglocality = st.session_state['loglocality']
        logcountry = st.session_state['logcountry']
        category = st.session_state['category']
        rating = st.session_state['rating']
        mydate = str(st.session_state['mydate'])
        comment = st.session_state['comment']
        mykey = mydate+"_"+loglocality
        image_file = st.session_state['image_file']
        bytedata = image_file.read()
        image_url = upload_to_bucket(image_file.name, image_file.type,  bytedata, bucket_name)

        # print(image_url, image_file.name, image_file.type, bucket_name)
        db.insert_location(mykey, loglocality, logcountry, loglat, loglon, category, rating, mydate, comment, image_url)
        st.success('Success!', icon="✅")

    # folium.Marker(location=[loglat, loglon], popup=loglocality,
    #     icon=folium.Icon(icon='glass')).add_to(m)


# app = Nominatim(user_agent="tutorial")

# if output['all_drawings']:
#     drawingpoints = output['all_drawings']

#     for pnt in drawingpoints:
#         coord = pnt['geometry']['coordinates']
#         lon = coord[0]
#         lat = coord[1]
#         address = get_address_by_location(lat, lon, geolocator)
#         display_name = address['display_name']

        # folium.Marker(
        #     [lat, lon],
        #     popup=display_name,
        #     tooltip=lon).add_to(m)

# output = st_folium(m, width=725, height=500, key='test2')



