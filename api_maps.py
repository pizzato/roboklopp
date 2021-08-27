from api_football import APIFootballExtended
from fpldata import FPLData
import pandas as pd
import json
import os

FOLDER = 'data/map_'

class APIMaps:
    def __init__(self, fpl: FPLData, afe: APIFootballExtended):
        self.fpl = fpl
        self.afe = afe

        self._map_team_ba, self._map_team_ab = self._load_maps('teams')
        self._map_gw_round, self._map_round_gw = self._load_maps('gw_round')
        self._map_players_ab, self._map_players_ba = self._load_maps('players')
        self._map_fixture_ab, self._map_fixture_ba = self._load_maps('fixtures')

    def _load_maps(self, name):
        fn = FOLDER + '{name}.json'.format(name=name)
        if os.path.isfile(fn):
            with open(fn, 'r', encoding='utf-8') as f:
                map_ab, map_ba = json.load(f)
            return map_ab, map_ba
        else:
            return None, None

    def _save_map(self, name, map_ab, map_ba):
        fn = FOLDER + '{name}.json'.format(name=name)
        with open(fn, 'w', encoding='utf-8') as f:
            json.dump((map_ab, map_ba), f, ensure_ascii=False, indent=4)

    def get_map_teams(self):
        if self._map_team_ab is None or self._map_team_ba is None:

            info_a = self.fpl.fetch_info()
            teams_b = self.afe.get_map_team_name_id()

            df_team_a = info_a['teams'][['code', 'id', 'short_name', 'name']]
            df_team_a = df_team_a.rename({c: c + "_a" for c in df_team_a.columns}, axis=1)

            df_team_b = pd.DataFrame(teams_b.items(), columns=["name_b", "id_b"])

            df_team_ab = pd.merge(df_team_a, df_team_b, left_on="name_a", right_on="name_b")

            _tmp_a = df_team_a[~df_team_a.name_a.isin(df_team_b.name_b)]
            _tmp_b = df_team_b[~df_team_b.name_b.isin(df_team_a.name_a)].copy().sort_values('name_b')
            _tmp_b['short_name_a'] = sorted(["MCI", "MUN", "TOT"])  # this is valid for premier league, 2021
            _tmp_ab = pd.merge(_tmp_a, _tmp_b, on="short_name_a")

            df_team_ab = df_team_ab.append(_tmp_ab).reset_index(drop=True)
            self._map_team_ab = df_team_ab[['id_a', 'id_b']].set_index('id_a')['id_b'].to_dict()
            self._map_team_ba = df_team_ab[['id_a', 'id_b']].set_index('id_b')['id_a'].to_dict()

            self._save_map('teams', self._map_team_ab, self._map_team_ba)

        return self._map_team_ab, self._map_team_ba


    def get_map_gw_round(self):
        if self._map_gw_round is None or self._map_round_gw is None:
            info_a = self.fpl.fetch_info()

            game_week_a = info_a['events'][['id','name','deadline_time','finished', 'is_current', 'is_next']].copy()
            round_b = self.afe.round()

            df_gameweek_round = pd.concat([game_week_a, round_b], axis=1)

            self._map_gw_round = df_gameweek_round[['name','rounds']].set_index('name')['rounds'].to_dict()
            self._map_round_gw = df_gameweek_round[['rounds','name']].set_index('rounds')['name'].to_dict()

            self._save_map('gw_round', self._map_gw_round, self._map_round_gw)

        return self._map_gw_round, self._map_round_gw


    def get_map_players(self):
        if self._map_players_ab is None or self._map_players_ba is None:
            info_a = self.fpl.fetch_info()

            players_a = info_a['elements'][['id','code','element_type','first_name','second_name',
                                            'status','team','web_name']].copy()
            players_a["first_name"] = players_a["first_name"].str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')
            players_a["second_name"] = players_a["second_name"].str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')
            players_a["web_name"] = players_a["web_name"].str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')

            players_a['name'] = players_a.first_name.str.get(0) + '. ' + players_a.second_name
            players_a['fullname'] = players_a.first_name + ' ' + players_a.second_name
            players_a['fullname'] = players_a['fullname'].str.strip()

            players_a = players_a.rename({'team':'team_id'}, axis=1)

            players_b = self.afe.get_league_players()
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

            self._map_players_ab = player_ab.set_index("id_a")["id_b"].to_dict()
            self._map_players_ba = player_ab.set_index("id_b")["id_a"].to_dict()

            self._save_map('players', self._map_players_ab, self._map_players_ba)
        return self._map_players_ab, self._map_players_ba

    def get_map_fixtures(self):

        if self._map_fixture_ab is None or self._map_fixture_ab is None:
            map_team_ab, _ = self.get_map_teams()

            cols_a = ['id', 'team_h', 'team_a']
            cols_b = ['fixture_id', 'teams_home_id', 'teams_away_id']

            fix_a = self.fpl.fetch_fixtures()[cols_a].copy()
            fix_b = self.afe.fixtures()[cols_b].copy()

            fix_a['index_ha'] = fix_a.team_h.map(map_team_ab).astype(str) + ':' + fix_a.team_a.map(map_team_ab).astype(str)
            fix_a = fix_a.set_index('index_ha')

            fix_b['index_ha'] = fix_b.teams_home_id.astype(str) + ':' + fix_b.teams_away_id.astype(str)
            fix_b = fix_b.set_index('index_ha')

            fix_ab = pd.merge(fix_a, fix_b, on='index_ha')

            self._map_fixture_ab = fix_ab.set_index('id')['fixture_id'].to_dict()
            self._map_fixture_ba = fix_ab.set_index('fixture_id')['id'].to_dict()

            self._save_map('fixtures', self._map_fixture_ab, self._map_fixture_ba)

        return self._map_fixture_ab, self._map_fixture_ba


