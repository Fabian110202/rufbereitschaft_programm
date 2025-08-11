import requests
from datetime import datetime

class FeiertageAPI:
    BASE_URL = 'https://feiertage-api.de/api/'
    LAND_NRW = 'NW'

    _cache = {}

    @classmethod
    def get_feiertage_von_land(cls, jahr):
        cache_key = f'feiertage_{jahr}_{cls.LAND_NRW}'
        if cache_key in cls._cache:
            return cls._cache[cache_key]

        params = {
            'jahr': jahr,
            'nur_land': cls.LAND_NRW
        }
        response = requests.get(cls.BASE_URL, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        cls._cache[cache_key] = data
        return data

    @classmethod
    def is_feiertag_in_land(cls, datum):
        # datum im Format 'YYYY-MM-DD'
        try:
            dt = datetime.strptime(datum, '%Y-%m-%d')
        except ValueError:
            raise ValueError("Datum muss im Format 'YYYY-MM-DD' sein")

        feiertage = cls.get_feiertage_von_land(dt.year)
        for feiertag in feiertage.values():
            if feiertag['datum'] == datum:
                return True
        return False


# Beispielnutzung:
if __name__ == "__main__":
    jahr = 2025
    feiertage_nrw = FeiertageAPI.get_feiertage_von_land(jahr)
    print(f"Feiertage in NRW für {jahr}:")
    for name, info in feiertage_nrw.items():
        print(f"{info['datum']}: {name}")

    datum_test = '2025-10-03'
    print(f"Ist {datum_test} ein Feiertag in NRW? {FeiertageAPI.is_feiertag_in_land(datum_test)}")
