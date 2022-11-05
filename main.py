import streamlit as st
from shapely.geometry import Point, Polygon
import geopandas as gpd
import pandas as pd
import geopy
import folium
from folium.plugins import Draw, BeautifyIcon
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

from country_list import countries_for_language

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

# -------------- DATA ----------------------------
dataitems = db.fetch_all_data()
# all_countries = [item['country'] for item in dataitems]
countries = dict(countries_for_language('en'))
all_countries = list(countries.values())
country_default_index = all_countries.index('Singapore')
# -------------- SIDEBAR -------------------------
st.sidebar.title("Search")

# street = st.sidebar.text_input("Street", "75 Bay Street")
# city = st.sidebar.text_input("City", "Toronto")
# province = st.sidebar.text_input("Province", "Ontario")
# country = st.sidebar.text_input("Country", "Singapore", key='search_country')
country = st.sidebar.selectbox("Search country", all_countries,
    index=country_default_index, key='search_country')
locality = st.sidebar.text_input("Location", key='search_locality')

country = st.session_state['search_country']
locality = st.session_state['search_locality']

# st.write("-------------")
# width_map = st.sidebar.number_input("Map Width", 250)

# -------------- MAP -------------------------------------
geolocator = Nominatim(user_agent="GTA Lookup")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
# location = geolocator.geocode(street+", "+city+", "+province+", "+country)
if locality!='':
    location = geolocator.geocode(locality+", "+country)
    initial_zoom = 15
else:
    location = geolocator.geocode(country)
    initial_zoom = 5


lat = location.latitude
lon = location.longitude

# map_data = pd.DataFrame({'lat': [lat], 'lon': [lon]})
# st.map(map_data)

# ---------- NAV MENU ----------------
select_options = ["Map", "Entry"]
selected = option_menu(menu_title=None,
    options=select_options,
    icons=["bar-chart-fill", "pencil-fill"], # https://icons.getbootstrap.com
    orientation='horizontal')

# Folium
m = folium.Map(location=[lat, lon], zoom_start=initial_zoom) #tiles='CartoDB dark_matter'

# Getting data from DETA and create dataframe
cols = ['key', 'latitude', 'longitude', 'location', 'country', 'category', 'rating', 'period', 'comment', 'image']
all_cat = ["Food", "Drink", "Shopping", "Activity", "Accomodation", "View Point"]
caticon = {all_cat[0]:'leaf', all_cat[1]:'glass', all_cat[2]:'gift', all_cat[3]:'bicycle', all_cat[4]:'home', all_cat[5]:'camera'}
catcol = {all_cat[0]:'coral', all_cat[1]:'darkturquoise', all_cat[2]:'palegreen', all_cat[3]:'#FEA3AA', all_cat[4]:'#9E7BFF', all_cat[5]:'#E9AB17'}

def retrieve_markers(dataitems, df, all_cat, caticon, catcol, draggable):
    for item in dataitems:
        dkey = item['key']
        dlat = item['latitude']
        dlon = item['longitude']
        dloc = item['locality']
        dcon = item['country']
        dcat = item['category']
        drat = item['rating']
        dper = item['period']
        dcom = item['comment']
        dima = item['image']
        df.loc[len(df)] = [dkey, dlat, dlon, dloc, dcon, dcat, drat, dper, dcom, dima]

        # Folium Marker
        folium.Marker(location=[dlat, dlon], popup=dloc, draggable=draggable,
            icon=BeautifyIcon(icon=caticon[dcat], icon_shape="marker",
                border_color=catcol[dcat], background_color=catcol[dcat])).add_to(m)
            # icon=folium.Icon(icon=caticon[dcat], color=catcol[dcat])).add_to(m)
        return df

df = pd.DataFrame(columns=cols)
draggable = False
df = retrieve_markers(dataitems, df, all_cat, caticon, catcol, draggable)

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
                for key in dispima:
                    st.image(dispima[key], use_column_width='always')

def upload_to_bucket(blob_name, blob_type, bytedata, bucket_name):
    """ Upload data to a google cloud bucket and get public URL"""
    # Explicitly use service account credentials by specifying the private key
    # file.
    bucket = client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(bytedata, content_type=blob_type)
    # returns a public url
    # blob.make_public()
    # return f'https://storage.cloud.google.com/{bucket_name}/{blob_name}'
    return f'https://storage.googleapis.com/{bucket_name}/{blob_name}'

if selected == select_options[1]:
    # Add marker
    col1, col2 = st.columns([1,1])
    with col1:
        # m = folium.Map(location=[lat, lon], draggable=True, zoom_start=initial_zoom)
        df = pd.DataFrame(columns=cols)
        draggable = True
        df = retrieve_markers(dataitems, df, all_cat, caticon, catcol, draggable)
        Draw().add_to(m) # Draw(export=True)
        output = st_folium(m, width=350, height=450) #width=725
        # print(output)

    with col2:
        try:
            last_obj_inp = output['last_object_clicked']
        except:
            last_obj_inp = ''
        if last_obj_inp:
            loglat = last_obj_inp['lat']
            loglon = last_obj_inp['lng']
            dff = df[(df['latitude']==loglat)&(df['longitude']==loglon)]
            dispkey = dff.iloc[0]['key']
            disploc = dff.iloc[0]['location']
            dispcon = dff.iloc[0]['country']
            dispcat = dff.iloc[0]['category']
            disprat = dff.iloc[0]['rating']
            dispper = dff.iloc[0]['period']
            dispcom = dff.iloc[0]['comment']
            dispima = dff.iloc[0]['image']
            cat_index = all_cat.index(dispcat)
            loglocality = st.text_input("Location", disploc, key='loglocality')
            logcountry = st.text_input("Country", dispcon, key='logcountry')
            category = st.selectbox("Category", all_cat, index=cat_index, key='category')
            rating = st.radio("Star", (1, 2, 3, 4, 5), index=disprat-1, horizontal=True, key='rating')
            mydate = st.date_input("Date", datetime.strptime(dispper, '%Y-%m-%d'), key='mydate')
            comment = st.text_area('Comments', dispcom, key='comment')

            imgselect = [dispima[key].split('/')[-1] for key in dispima]
            imgoptions = st.multiselect('Select your images', imgselect, imgselect)
            imglinkdict = dict()
            for imgname in imgoptions:
                imglink = f'https://storage.googleapis.com/{bucket_name}/{imgname}'
                imglinkdict[imgname] = imglink
                st.markdown(imgname)
                st.image(imglink, use_column_width='always')
            image_files = st.file_uploader("Upload More Images", type=["png","jpg","jpeg"],
                accept_multiple_files=True, key='image_files')
            for image_file in image_files:
                st.image(load_image(image_file), width=250)

        else:
            loglocality = st.text_input("Location", key='loglocality')
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

            image_files = st.file_uploader("Upload Images", type=["png","jpg","jpeg"],
                accept_multiple_files=True, key='image_files')
            for image_file in image_files:
                st.image(load_image(image_file), width=250)

    # if last_obj_inp:
    #     for key in dispima:
    #         st.image(dispima[key], use_column_width='always')
    # else:
    #     image_files = st.file_uploader("Upload Images", type=["png","jpg","jpeg"],
    #         accept_multiple_files=True, key='image_files')
    #     for image_file in image_files:
    #         st.image(load_image(image_file), width=250)

        dictimages = {}
        if st.button("Submit"):

            if last_obj_inp:
                loglocality = st.session_state['loglocality']
                logcountry = st.session_state['logcountry']
                category = st.session_state['category']
                rating = st.session_state['rating']
                mydate = str(st.session_state['mydate'])
                comment = st.session_state['comment']
                mykey = dispkey
                image_files = [image_file for image_file in st.session_state['image_files']]
                for image_file in image_files:
                    bytedata = image_file.read()
                    image_url = upload_to_bucket(image_file.name, image_file.type,  bytedata, bucket_name)
                    imglinkdict[image_file.name]=image_url
                # print(imglinkdict)
                dictimages = imglinkdict
            else:
                loglocality = st.session_state['loglocality']
                logcountry = st.session_state['logcountry']
                category = st.session_state['category']
                rating = st.session_state['rating']
                mydate = str(st.session_state['mydate'])
                comment = st.session_state['comment']
                mykey = mydate+"_"+loglocality
                image_files = [image_file for image_file in st.session_state['image_files']]
                for image_file in image_files:
                    bytedata = image_file.read()
                    image_url = upload_to_bucket(image_file.name, image_file.type,  bytedata, bucket_name)
                    dictimages[image_file.name]=image_url

            # print(image_url, image_file.name, image_file.type, bucket_name)
            db.insert_location(mykey, loglocality, logcountry, loglat, loglon, category, rating, mydate, comment, dictimages)
            st.success('Success!', icon="✅")




