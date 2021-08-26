from api_football import APIFootballExtended
from fpldata import FPLData
import pandas as pd

key = "<KEY>"
league = 39
season = 2021

fpl = FPLData()
afe = APIFootballExtended(key=key, league=league, season=season)


def match_teams():

    info_a = fpl.fetch_info()
    teams_b = afe.get_map_team_name_id()

    df_team_a = info_a['teams'][['code', 'id', 'short_name', 'name']]
    df_team_a = df_team_a.rename({c: c + "_a" for c in df_team_a.columns}, axis=1)

    df_team_b = pd.DataFrame(teams_b.items(), columns=["name_b", "id_b"])

    df_team_ab = pd.merge(df_team_a, df_team_b, left_on="name_a", right_on="name_b")

    _tmp_a = df_team_a[~df_team_a.name_a.isin(df_team_b.name_b)]
    _tmp_b = df_team_b[~df_team_b.name_b.isin(df_team_a.name_a)].copy().sort_values('name_b')
    _tmp_b['short_name_a'] = sorted(["MCI", "MUN", "TOT"])  # this is valid for premier league, 2021
    _tmp_ab = pd.merge(_tmp_a, _tmp_b, on="short_name_a")

    df_team_ab = df_team_ab.append(_tmp_ab).reset_index(drop=True)
    map_team_ab = df_team_ab[['id_a', 'id_b']].set_index('id_a')['id_b'].to_dict()
    map_team_ba = df_team_ab[['id_a', 'id_b']].set_index('id_b')['id_a'].to_dict()
    return df_team_ab, map_team_ab, map_team_ba

def match_gameweek_round():

    info_a = fpl.fetch_info()

    game_week_a = info_a['events'][['id','name','deadline_time','finished', 'is_current', 'is_next']].copy()
    round_b = afe.round()

    df_gameweek_round = pd.concat([game_week_a, round_b], axis=1)

    map_gameweek_round = df_gameweek_round[['name','rounds']].set_index('name')['rounds'].to_dict()
    map_round_gameweek = df_gameweek_round[['rounds','name']].set_index('rounds')['name'].to_dict()

    return df_gameweek_round, map_gameweek_round, map_round_gameweek


def match_players():
    info_a = fpl.fetch_info()

    players_a = info_a['elements'][['id','code','element_type','first_name','second_name',
                                    'status','team','web_name']].copy()
    players_a["first_name"] = players_a["first_name"].str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')
    players_a["second_name"] = players_a["second_name"].str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')
    players_a["web_name"] = players_a["web_name"].str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')

    players_a['name'] = players_a.first_name.str.get(0) + '. ' + players_a.second_name
    players_a['fullname'] = players_a.first_name + ' ' + players_a.second_name
    players_a['fullname'] = players_a['fullname'].str.strip()

    players_a = players_a.rename({'team':'team_id'}, axis=1)

    players_b = afe.get_league_players()
    # normalise and remove accents
    players_b["name"] = players_b["name"].str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')

    player_ab = pd.merge(players_a, players_b, on='name', suffixes=('_a','_b'))
    print("Matched players: {} of at least {}".format(len(player_ab), max(len(players_a), len(players_b))))

    players_a_m2 = players_a[~players_a.id.isin(player_ab.id_a)]
    print("Not matched in A: ", len(players_a_m2))

    tmp_player_ab = pd.merge(players_a_m2, players_b, left_on='web_name', right_on='name', suffixes=('_a','_b'))
    print("Extra webname matched: ", len(tmp_player_ab))
    player_ab = player_ab.append(tmp_player_ab).reset_index(drop=True)
    print("New match size: ", len(player_ab))
    players_a_m2 = players_a[~players_a.id.isin(player_ab.id_a)]
    print("Not matched in A: ", len(players_a_m2))

    tmp_player_ab = pd.merge(players_a_m2, players_b, left_on='fullname', right_on='name', suffixes=('_a','_b'))
    print("Extra webname matched: ", len(tmp_player_ab))
    player_ab = player_ab.append(tmp_player_ab).reset_index(drop=True)
    print("New match size: ", len(player_ab))
    players_a_m2 = players_a[~players_a.id.isin(player_ab.id_a)].copy()
    print("Not matched in A: ", len(players_a_m2))

    players_b_m2 = players_b[~players_b.id.isin(player_ab.id_b)]
    print("Not matched in B: ", len(players_b_m2))

    # This matching was done recording the files and then manually matching
    # players_a_m2.sort_values('team_id').to_csv('no_match_team_a.csv')
    # players_b_m2.sort_values('team_id').to_csv('no_match_team_b.csv')

    # Manual Job to match players: find data in
    map_player_manual_match = pd.read_csv('data/players_manual_match.csv')
    map_player_manual_a_b = map_player_manual_match.set_index("id_a")["id_b"].to_dict()
    print("Number of manual matches:", len(map_player_manual_a_b))

    players_a_m2['id_a_mapped_b'] = players_a['id'].map(map_player_manual_a_b)
    players_a_m3 = players_a_m2[~players_a_m2.id_a_mapped_b.isnull()].copy()
    players_a_m3.id_a_mapped_b =  players_a_m3.id_a_mapped_b.astype(int)

    player_ab_manual = pd.merge(players_a_m3, players_b, left_on='id_a_mapped_b', right_on='id', suffixes=('_a','_b'))

    player_ab = player_ab.append(player_ab_manual).reset_index(drop=True)
    print("New match size: ", len(player_ab))

    map_players_ab = player_ab.set_index("id_a")["id_b"].to_dict()
    map_players_ba = player_ab.set_index("id_b")["id_a"].to_dict()

    return player_ab, map_players_ab, map_players_ba
