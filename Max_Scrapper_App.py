# importer packages
import pandas as pd
import requests
from bs4 import BeautifulSoup as bs # permet de stocker le code html dans un objet beautifulsoup
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import undetected_chromedriver as uc
import time
from undetected_chromedriver import Chrome
import numpy as np
import sqlite3 as sql
import streamlit as st
import matplotlib.pyplot as plt
from io import StringIO
import os


# Créer une base de données
#con=sql.connect('data/data.db')
# Créer un cursor
#c=con.cursor()
# Créer les tables de stockages des données
#c.execute('''CREATE TABLE computer(details , prix, etat, marque, adresse, image_lien)''')
#c.execute('''CREATE TABLE phone(details , prix, etat, marque, adresse, image_lien)''')
#c.execute('''CREATE TABLE home_cinema(details , prix, etat, marque, adresse, image_lien)''')
#con.commit()
#con.close()

# create function to input start and end page
def input_pages():
    x = st.number_input("Page de début", min_value=1, value=1, step=1)
    y = st.number_input("Page de fin", min_value=x, value=1, step=1)
    return x,y

# create function to scrap computer data on multiple pages
def scrap_data(product,x,y):
    """_summary_ : function to scrapp data from https://www.expat-dakar.com/
    
    Args:
        product: url of kind of products to scrapp
        x (_type_): start page
        y (_type_): end_page

    Returns:
        _type_: dataframe of all data scrapped
    """
    # Ensure ChromeDriver has executable permissions
    os.chmod("chromedriver-linux64/chromedriver", 0o755)
    # Create empty dataframe
    df_c=pd.DataFrame()
    # loop over all pages
    for p in range(x,y+1):
        # Get the URL
        url="https://www.expat-dakar.com/{}?page={}".format(product,p)
        # Set Chrome options
        chrome_options = uc.ChromeOptions()
        # Path to binary location
        chrome_options.binary_location = "chromedriver-linux64/chromedriver"
        chrome_options.add_argument("--headless")  # Run in headless mode
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        # Services
        chrome_services=Service("chromedriver-linux64/chromedriver")
        #Create a undetectable chrome driver
        chrome=uc.Chrome(service=chrome_services, options=chrome_options)
        # Get the URL infos
        chrome.get(url)
        # Wait for the page to load for 60 seconds to ensure pass the 'just a moment'
        time.sleep(30)
        # Get the html code of page
        res  = chrome.page_source
        # Stock the html code in beautiful soup object
        soup = bs(res, 'html.parser')
        # get all containers on the page
        containers = soup.find_all('div', class_  = 'listings-cards__list-item')
        
        # Create a list to store the data by page
        data_list = []
        # Loop through all the containers
        for container in containers:
            try:
                # Get the url of containers
                url_container = container.find('a', class_ = 'listing-card__inner')['href']
                chrome.get(url_container)
                time.sleep(20)
                res_c = chrome.page_source
                soup_c = bs(res_c, 'html.parser')
                # Get info from each computer
                details = soup_c.find('h1', class_ = 'listing-item__header').text.strip()
                prix = soup_c.find('span',class_ = 'listing-card__price__value 1').text.strip()
                titre = soup_c.find_all('dt', class_ = 'listing-item__properties__title')
                descripteur = soup_c.find_all('dd', class_ = 'listing-item__properties__description')
                # Get state and brand who are in same container
                data = {}
                for title, desc in zip(titre, descripteur):
                    data[title.text.strip()] = desc.text.strip()
                for key, value in data.items():
                    if key == 'Marque':
                        marque = value
                    if key == 'Etat':
                        etat = value
                adresse= soup_c.find('div', class_ = 'listing-item__address').text.strip().replace('\n', ' ')
                
                image_lien=soup_c.find('div', class_ = 'gallery__image__inner').img['src']
                
                #Store all data in a dictionary
                dict_ = {'details': details, 'prix': prix, 'etat': etat, 'marque': marque, 'adresse': adresse,'lien_image':image_lien}
                data_list.append(dict_)
            except:
                pass
            df=pd.DataFrame(data_list)
            df_c = pd.concat([df_c,df], axis = 0).reset_index(drop = True)
        # Close the browser
        chrome.quit()
    return df_c

# download button
def show_data_button(df):
    st.subheader('Display data dimension')
    st.write('Data dimension: ' + str(df.shape[0]) + ' rows and ' + str(df.shape[1]) + ' columns.')
    st.dataframe(df)

def instantiate_scrapping(articles,table):
    if "df_c" not in st.session_state:
            st.session_state.df_c = None  # Initialize session variable
    if st.button("Scrapper les données"):
            st.session_state.df_c = scrap_data(articles, x, y)  # Store data persistently
    if st.session_state.df_c is not None and not st.session_state.df_c.empty:
        if st.button("Voir les données"):
            show_data_button(st.session_state.df_c)  # show data scrapped
        
        # Insert rows from data scrapped into existing table 
        # Create a connection to a sqlite database
        con = sql.connect('data/data.db')
        st.session_state.df_c.to_sql(f"{table}", con, if_exists='replace', index=False) # insert data into table
        st.success(f'{len(st.session_state.df_c)} {articles} inséré dans la base de données')
        con.commit()
        con.close()

def get_registred_data(filename):
    df=pd.read_csv(f"data/{filename}.csv")
    df=df.drop(df.columns[0],axis=1)
    df['prix']=pd.to_numeric(df['prix'].str.replace("F Cfa","").str.replace(' ','').str.replace(' ','').str.strip(),errors='coerce')
    return df

def dashboard_chart(df,column: list,chart_type,color="#00FF00",height=150,width=50):
    chart_data=df[[column]].copy()
    if chart_type=="Bar":
        st.title(f"graphe des {column}")
        st.bar_chart(chart_data,y=column,color=color,height=height)
    if chart_type=="Pie":
        val=chart_data.value_counts()
        fig, ax=plt.subplots(figsize=(8, 6))
        ax.pie(val,labels=val.index,autopct='%1.1f%%',startangle=90)
        ax.axis('equal')
        st.title(f"graphe des {column}")
        st.pyplot(fig)

def show_dashboard(articles):
    opt= st.radio("Type de donnée",["Numériques","Catégories"])
    df=get_registred_data(articles)
    if opt=="Numériques":
        dashboard_chart(df,'prix',"Bar","#00FF00")
    if opt=="Catégories":
        for col in ['etat','marque']:
            dashboard_chart(df,col,"Pie")

def embed_kobo():
    st.title("Formulaire d'évaluation de l'application")
    # My Kobo HTML snippet with responsive design
    kobo_html_snippet = """
    <style>
        .iframe-container {
            position: relative;
            overflow: hidden;
            width: 100%;
            padding-top: 150%; /* adjust to screen frame size */
        }
        .iframe-container iframe {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            border: none;
        }
    </style>
    <div class="iframe-container">
        <iframe src="https://ee.kobotoolbox.org/i/gMmjrFWX"></iframe>
    </div>
    """
    # Display the HTML snipset in Streamlit
    st.components.v1.html(kobo_html_snippet, height=900)

# Fetch kobo data from the CSV API link
def fetch_kobo_csv_data(api_token, csv_api_url):
    headers = {"Authorization": f"Token {api_token}"}
    response = requests.get(csv_api_url, headers=headers)
    
    # Check if the request was successful
    if response.status_code == 200:
        # Load the CSV data into a Pandas DataFrame
        csv_data = StringIO(response.content.decode("UTF-8"))
        df = pd.read_csv(csv_data,sep=";")
        return df
    else:
        print(f"Failed to fetch data: {response.status_code}")
        return pd.DataFrame()

# Streamlit app
## Set page config
st.markdown("<h1 style='text-align: center; color: GREEN;'>WEB SCRAPPING APP</h1>", unsafe_allow_html=True)

st.markdown("""
This app allow to scrapp data from 'https://www.expat-dakar.com/'
* **Python libraries:** requests, pandas, streamlit, bs4, selenium, time, numpy, undetected_chromedriver, sqlite3
* **Data source:** [Expat-Dakar](https://www.expat-dakar.com/).
""")


# Sidebar options
st.sidebar.title("MENU")
#Scrapping des données
option = st.sidebar.selectbox("scrapping des données", ["Ordinateurs","Téléphones","Home-cinéma"],index=None)
## Show input pages
if option:
    x,y=input_pages()
## Scrap data
if option=="Ordinateurs" and x >= 1 and y>=1:
    instantiate_scrapping("ordinateurs","computer")
if option=="Téléphones" and x >= 1 and y>=1:
    instantiate_scrapping("telephones","phones")
if option=="Home-cinéma" and x >= 1 and y>=1:
    instantiate_scrapping("tv-home-cinema","home_cinema")

#Affichage des données
option_data = st.sidebar.selectbox("Voire les données scrappées", ["Ordinateurs","Téléphones","Home-cinéma"],index=None)
if option_data=="Ordinateurs":
    df=get_registred_data("computer_data")
    show_data_button(df)
if option_data=="Téléphones":
    df=get_registred_data("phone_data")
    show_data_button(df)
if option_data=="Home-cinéma":
    df=get_registred_data("home_cinema_data")
    show_data_button(df)

#Affichage du dashboard
option_dashboard = st.sidebar.selectbox("Dashboards", ["Ordinateurs","Téléphones","Home-cinéma"],index=None)
if option_dashboard=="Ordinateurs":
    show_dashboard("computer_data")        
if option_dashboard=="Téléphones":
    show_dashboard("phone_data")        
if option_dashboard=="Home-cinéma":
    show_dashboard("home_cinema_data")        
    
#Evaluation de l'app
option_eval = st.sidebar.selectbox("Evaluation de l'app", ["Evaluation","Notation"],index=None)
if option_eval=="Evaluation":
    embed_kobo()
if option_eval=="Notation":
    df=fetch_kobo_csv_data("d1c7b20916181a17dccdd3c2e5c1d495180ea1aa","https://kf.kobotoolbox.org/api/v2/assets/auTg2SR2BFV6wXzoKGKppd/export-settings/esxeiUH4sSAYQGyzQqtSyax/data.csv")
    for col in ['Scraaping des données','Dashboard','Téléchargement des données']:
        dashboard_chart(df,col,"Bar",height=175)
