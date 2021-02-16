from datetime import datetime

import requests


BASE_URL = "https://disease.sh/v3/covid-19/"


class CovidApi:
    """A simple wrapper for the COVID-19 disease.sh API (https://github.com/disease-sh/API)."""

    def __init__(self):
        self.countries = self._all_countries()
        self.name_map = self._build_name_map(self.countries)
        self.us_states = self._all_us_states()
        self.de_states = self._all_de_states()

    def _clean(self, s):
        s = s.replace("\xad", "")
        s = s.replace("\n", "")
        return s

    def _build_name_map(self, countries):
        name_map = {}
        for iso2, country in countries.items():
            name_map[country["iso2"].lower()] = iso2
            name_map[country["iso3"].lower()] = iso2
            name_map[country["name"].lower()] = iso2
        return name_map

    def _all_countries(self):
        response = requests.get(BASE_URL + "countries")
        if response.status_code == 200:
            countries = {}
            for item in response.json():
                iso2 = item["countryInfo"]["iso2"]
                if iso2:
                    countries[iso2] = item["countryInfo"]
                    countries[iso2]["name"] = item["country"]
            return countries
        else:
            return {}

    def _all_us_states(self):
        response = requests.get(BASE_URL + "states")
        if response.status_code == 200:
            countries = []
            for item in response.json():
                countries.append(item["state"])
            return countries
        else:
            return []

    def _all_de_states(self):
        response = requests.get(BASE_URL + "gov/de")
        if response.status_code == 200:
            countries = []
            for item in response.json():
                if item["province"].lower() != "total":
                    countries.append(self._clean(item["province"]))
            return countries
        else:
            return []

    def cases_world(self):
        response = requests.get(BASE_URL + "all")
        if response.status_code == 200:
            return response.json()
        else:
            return None

    def cases_country_list(self, sort_by="cases"):
        response = requests.get(BASE_URL + "countries", params={"sort": sort_by})
        if response.status_code == 200:
            return [item for item in response.json() if item["countryInfo"]["iso2"]]
        else:
            return []

    def cases_country(self, country):
        country_code = self.name_map[country.lower()]
        response = requests.get(BASE_URL + "countries/{}".format(country_code))
        if response.status_code == 200:
            data = response.json()
            del data["countryInfo"]
            return data
        else:
            return None

    def cases_us_state(self, state):
        response = requests.get(BASE_URL + "states/{}".format(state))
        if response.status_code == 200:
            data = response.json()
            # additions to unify format with countries
            data["recovered"] = data["cases"] - data["active"] - data["deaths"]
            return data
        else:
            return None

    def cases_de_state(self, state):
        response = requests.get(BASE_URL + "gov/de")
        if response.status_code == 200:
            data = response.json()
            filtered = [item for item in data if self._clean(item["province"].lower()) == state.lower()]
            return filtered[0] if len(filtered) > 0 else None
        else:
            return None

    def timeseries(self, country=None, days=40):
        # we always request one additional day to be able to calculate diffs
        if not country:
            response = requests.get(BASE_URL + "historical/all", params={"lastdays": days + 1})
        else:
            country_code = self.name_map[country.lower()]
            response = requests.get(BASE_URL + "historical/{}".format(country_code), params={"lastdays": days + 1})
        if response.status_code == 200:
            data = response.json()
            if "timeline" in data:  # if for a specific country
                name = data["country"]
                data = data["timeline"]
            else:
                name = "the World"
            sorted_dates = sorted(data["cases"], key=lambda s: datetime.strptime(s, "%m/%d/%y"))
            cases, deaths = [], []
            for i in range(1, len(sorted_dates)):
                today, yesterday = sorted_dates[i], sorted_dates[i - 1]
                cases.append(data["cases"][today] - data["cases"][yesterday])
                deaths.append(data["deaths"][today] - data["deaths"][yesterday])
            return {
                "name": name,
                "first_date": datetime.strptime(sorted_dates[1], "%m/%d/%y"),
                "cases": cases,
                "deaths": deaths,
            }
        else:
            return None