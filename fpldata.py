import requests
import pandas as pd

# Base URLs

_EP_BASE = "https://fantasy.premierleague.com/api/"
_EP_INFO = _EP_BASE + "bootstrap-static/"
_EP_FIXTURES = _EP_BASE + "fixtures/"
_EP_ELEMENT = _EP_BASE + "element-summary/{element_id}/"
_EP_GAMEWEEK = _EP_BASE + "event/{game_week}/live/"
_EP_MANAGER = _EP_BASE + "entry/{manager_id}/"
_EP_MANAGER_HISTORY = _EP_BASE + "entry/{manager_id}/history"
_EP_LEAGUE_STANDING = _EP_BASE + "leagues-classic/{league_id}/standings?page_standings={page}"
_EP_MYTEAM = _EP_BASE + "my-team/{manager_id}/"
_EP_LOGIN = "https://users.premierleague.com/accounts/login/"
_EP_LOGIN_REDIRECT = "https://fantasy.premierleague.com/a/login"
_MAX_GAME_WEEKS = 38


class FPLData:
    """
    FPLData class that fetches data from FPL API and stores in a dictionary structure or pandas data frames.

        Data is return on each function and also stored in self.data
    """

    def __init__(self, convert_to_dataframes: bool = True, force_dataframes: bool = False):
        """

        :param convert_to_dataframes: boolean indicating that the data when possible will be converted to dataframes (default: True)
        :param force_dataframes: boolean indicating that non optimal dataframes such as simple vars are also converted to dataframes (default: False)
        """
        self._convert_to_dataframes = convert_to_dataframes
        self._force_dataframes = force_dataframes

        self.data = {}

    def fetch(self,
              info=True, fixtures=False, elements: list = None, game_week=False,
              managers: list = None, manager_history=False,
              leagues: list = None, all_standings=False
              ):
        """

        :param info:
        :param fixtures:
        :param elements:
        :param game_week:
        :param managers:
        :param manager_history:
        :param leagues:
        :param all_standings:
        :return: dict
        """

        if info:
            self.fetch_info()

        if fixtures:
            self.fetch_fixtures()

        if elements:
            self.fetch_elements(element_ids=elements)

        if game_week:
            self.fetch_game_week()

        if managers:
            self.fetch_managers(manager_ids=managers)

        if manager_history:
            self.fetch_managers_history(manager_ids=managers)

        if leagues:
            self.fetch_leagues(league_ids=leagues, get_all_standings=all_standings)

    def fetch_info(self):
        """
        Fetches info
        :return: dict
        """

        data_ = requests.get(_EP_INFO).json()

        if self._convert_to_dataframes:
            for k in data_.keys():
                if k in ['events', 'phases', 'teams', 'elements', 'element_types']:
                    data_[k] = pd.DataFrame(data_[k])
                elif self._force_dataframes:
                    try:
                        data_[k] = pd.DataFrame([data_[k]]).T
                    except ValueError:
                        pass

        self.data['info'] = data_
        return data_

    def fetch_fixtures(self):
        """
        Fetches fixture info
        :return: dict
        """

        data_ = requests.get(_EP_FIXTURES).json()
        if self._convert_to_dataframes:
            data_ = pd.DataFrame(data_)

        self.data['fixtures'] = data_
        return data_

    def fetch_elements(self, element_ids: list):
        """
        Fetches info for all elements (players) in list
        :param element_ids: list of element ids (players)
        :return: dict
        """

        data_ = {}
        for element_id in element_ids:
            dt_json = requests.get(_EP_ELEMENT.format(element_id=element_id)).json()

            data_[element_id] = dt_json \
                if not self._convert_to_dataframes \
                else {k: pd.DataFrame(dt_json[k]) for k in dt_json.keys()}

        self.data['elements'] = data_
        return data_

    def fetch_game_week(self):
        """
        Fetches all games weeks elements
        :return: dict
        """

        data_ = {}

        for gw in range(1, _MAX_GAME_WEEKS + 1):
            dt_json = requests.get(_EP_GAMEWEEK.format(game_week=gw)).json()

            data_[gw] = dt_json['elements'] \
                if not self._convert_to_dataframes \
                else pd.DataFrame(dt_json['elements'])

        self.data['game_week_elements'] = data_
        return data_

    def fetch_managers(self, manager_ids: list):
        """
        Fetches managers info
        :param manager_ids: list of ids for managers to get info         
        :return: dict
        """

        data_ = {}

        for manager_id in manager_ids:
            dt_json = requests.get(_EP_MANAGER.format(manager_id=manager_id)).json()

            data_[manager_id] = dt_json \
                if not self._convert_to_dataframes \
                else pd.DataFrame(dt_json)

        self.data['manager_id'] = data_
        return data_

    def fetch_managers_history(self, manager_ids: list):
        """
        Fetches managers history
        :param manager_ids: list of ids for managers to get info         
        :return: dict
        """

        data_ = {}

        for manager_id in manager_ids:
            dt_json = requests.get(_EP_MANAGER_HISTORY.format(manager_id=manager_id)).json()

            data_[manager_id] = dt_json \
                if not self._convert_to_dataframes \
                else {k: pd.DataFrame(dt_json[k]) for k in dt_json.keys()}

        self.data['manager_id_history'] = data_
        return data_

    def fetch_leagues(self, league_ids: list, get_all_standings=False):
        """
        Fetches leagues standings and other information
        :param league_ids: list of ids for all leagues to get standings
        :param get_all_standings: if there is pagination (many players), whether to get them all (default: False)
        :return: dict
        """

        data_ = {}

        for league_id in league_ids:
            dt_json = requests.get(_EP_LEAGUE_STANDING.format(league_id=league_id, page=1)).json()

            data_[league_id] = dt_json
            data_[league_id]['new_entries'] = dt_json['new_entries']['results']
            data_[league_id]['standings'] = dt_json['standings']['results']

            if get_all_standings:
                while dt_json['standings']['has_next']:
                    dt_json = requests.get(_EP_LEAGUE_STANDING.format(league_id=league_id, page=int(
                        dt_json['standings']['has_next']) + 1)).json()

                    data_[league_id]['standings'] += dt_json['standings']['results']

            if self._convert_to_dataframes:
                data_[league_id]['standings'] = \
                    pd.DataFrame(data_[league_id]['standings'])
            if self._force_dataframes:
                data_[league_id]['league'] = \
                    pd.DataFrame([data_[league_id]['league']]).T

        self.data['league_id'] = data_
        return data_

    def fetch_my_team(self, my_team, email, password):
        """
        Featch information about your team using email and password

        :param my_team: team_id
        :param email: email
        :param password: password
        :return: dict
        """
        with requests.Session() as session:

            payload = {
                'password': password,
                'login': email,
                'redirect_uri': _EP_LOGIN_REDIRECT,
                'app': 'plfpl-web'
            }
            session.post(_EP_LOGIN, data=payload)

            data_ = session.get(_EP_MYTEAM.format(manager_id=my_team)).json()

            if self._convert_to_dataframes:
                for k in ['picks', 'chips']:
                    data_[k] = pd.DataFrame(data_[k])

                if self._force_dataframes:
                    data_['transfers'] = pd.DataFrame([data_['transfers']]).T

            self.data['my_team'] = data_
            return data_
