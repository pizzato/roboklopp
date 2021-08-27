from api_football import APIFootballExtended
from fpldata import FPLData
from api_maps import APIMaps
import streamlit as st

key = st.secrets["api_football_key"]
league = 39
season = 2021

fpl = FPLData()
afe = APIFootballExtended(key=key, league=league, season=season)

def pre_compute_all_mappings():
    maps = APIMaps(fpl=fpl, afe=afe)
    maps.get_map_teams()
    maps.get_map_gw_round()
    maps.get_map_players()
    maps.get_map_fixtures()

if __name__ == "__main__":
    pre_compute_all_mappings()