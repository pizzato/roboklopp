import streamlit as st
import random

st.set_page_config(page_title="Robo Klopp", page_icon='images/roboklopp_eye.jpeg', layout="wide", initial_sidebar_state="auto", menu_items=None)

col1, col2 = st.columns([1, 3])

with col1:
    st.image('images/roboklopp{}.png'.format(random.randint(1, 10)))

with col2:
    """
          # Robo Klopp 
        
          ### What do you want Robo Klopp to do? 
          Select the options on the left.
          I can help you with 
          - this week's transfers, or; 
          - by creating a brand new team. 

          ---
          "humans coaches are overrated" -- Robo Klopp   
    """

