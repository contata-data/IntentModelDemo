import streamlit as st
from google.cloud import storage
from io import BytesIO
import os
import requests
import json
import pandas as pd
import time
import streamlit_extras
from streamlit_extras.switch_page_button import switch_page
from google.cloud import bigquery
import matplotlib.pyplot as plt

#relative_path = "relevate-dev-403605-3d2cdf274874.json"

# Get the absolute path dynamically
#credentials_path = os.path.join(os.getcwd(), relative_path)
##os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "\servicecert-relevate-dev-403605-991ce9234fb2.json"
#os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
#print(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))

# Load secrets from Streamlit cloud
#gcp_credentials = st.secrets["gcp_service_account"]

# Convert secrets to JSON format
gcp_credentials = dict(st.secrets["gcp_service_account"])  # Convert to a standard dictionary
service_account_json = json.dumps(gcp_credentials)

#service_account_json = json.dumps(gcp_credentials)

# Set up authentication
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/tmp/service_account.json"

# Save JSON file temporarily (Streamlit Cloud does not allow direct env vars for GCP)
with open("/tmp/service_account.json", "w") as f:
    f.write(service_account_json)

# Initialize Google Cloud Storage client
client = storage.Client()
bqclient = bigquery.Client()
# GCS bucket name
BUCKET_NAME = "relevate-dev-403605-list"

def intent_model_scores():
    sql = """
    select * from RelevateSystem.CustomerTopicScores
    order by score desc   
    """
    
    df = bqclient.query(sql).to_dataframe()
    return df

def generate_topics(payload):
    """Function to call the API and generate topics."""
    url = "https://us-central1-relevate-dev-403605.cloudfunctions.net/intentmodelgenerateusertopics"
    #print(url)  # Logging for debugging
    #print(payload)
    try:
        response = requests.post(url, json=payload)
        #response.raise_for_status()
        print(response.json())
        return response.json()  # Assuming the API returns JSON data
    except requests.exceptions.RequestException as e:
        st.error(f"API request failed: {e}")
        return None



def dashboard_page():
    df = pd.DataFrame()
    query = st.text_input("Enter your query", key="query", value="Whats on your mind?")
    timeRange = st.number_input("Enter timeRange", key="timeRange", min_value=0, step=1, value=10, format="%d")
    jobDuration = st.number_input("Enter jobDuration", key="jobDuration", min_value=0, step=1, value=10, format="%d")
    callbackUrl = "https://us-central1-relevate-dev-403605.cloudfunctions.net/intentmodelgenerateusertopics" #st.text_input("Enter callbackUrl", key="callbackUrl",value="https://us-central1-relevate-dev-403605.cloudfunctions.net/generateUserTopics")
    payload = {
        "query": query,
        "timeRange": int(timeRange),
        "jobDuration": int(jobDuration),
        "callbackUrl": callbackUrl
        }
    if st.button("Create Job"):
        with st.spinner("Creating Job, please wait..."):
            st.session_state.api_response = generate_topics(payload)
        data = st.session_state.api_response
        print(data)
        if data:
            if data["suggestedTopics"] == []:
                st.write("No relevant topics found.")
            else:
                st.session_state.data_list =  data["suggestedTopics"]
                ##col1 = st.columns([10])
                #for topic in st.session_state.data_list:
                st.write(data)
    for _ in range(5):
        st.write("")

    if st.button("Calculate intentModel scores"):
        with st.spinner("Calculating intentModel scores, please wait..."):
            st.session_state.df = intent_model_scores()  # Store df in session state

    # Check if df exists in session state before proceeding
    if "df" in st.session_state:
        df = st.session_state.df
        topics = st.session_state.data_list
        min_score, max_score = st.slider(
        "Select score range",
        min_value=0.0, max_value=3.0, value=(1.0, 2.0), step=0.01,
        key="score_range_slider"  # Unique key to prevent duplicate ID error
        )
        if "uuid" in df.columns:    
            df.pop("uuid")
        # Filter DataFrame based on selected score range
        filtered_df = df[(df["score"] >= min_score) & (df["score"] <= max_score) & (df["topic"].isin(topics))]

        st.write(f"Showing topics with score between {min_score} and {max_score}")
        st.write(filtered_df.head(50))

        # Plot histogram
        fig, ax = plt.subplots()
        ax.hist(filtered_df["score"], bins=20, color="blue", edgecolor="black")
        ax.set_xlabel("Score")
        ax.set_ylabel("Frequency")
        ax.set_title("Distribution of Intent Model Scores")

        st.pyplot(fig)
    
def main():
    

    if "page" not in st.session_state:
        st.session_state.page = "dashboard"
    if "api_response" not in st.session_state:
        st.session_state.api_response = None
    if "listType" not in st.session_state:
        st.session_state.listType = None
    if "bucket" not in st.session_state:
        st.session_state.bucket = None  
    
    st.title("Intent Model Dashboard")
    dashboard_page()
    
if __name__ == "__main__":
    main()
