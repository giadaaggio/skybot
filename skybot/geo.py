from dataclasses import dataclass
from typing import Any

import httpx

GEOCODING_URL = 'https://geocoding-api.open-meteo.com/v1/search'

@dataclass(frozen=True)
class Location: 
    name: str
    latitude: float
    longitude: float
    elevation_m: float | None
    timezone: str

# error handling
class CityNotFoundError(ValueError):
    ''' error raised when there is no matching city '''


class GeocodingError(RuntimeError):
    ''' error raised when geocoding fails or returns invalid data'''

# find city coordinates and local timezone
async def geocode_city(city: str) -> Location: 
    if not city.strip(): 
        raise CityNotFoundError('Inserisci il nome di una città.')

    try: 
        async with httpx.AsyncClient() as client: 
            response = await client.get(
                GEOCODING_URL,
                params = {'name': city, 'count': 1, 'language': 'it', 'format': 'json'}
            )
            response.raise_for_status()
            payload: Any = response.json()
    except (httpx.HTTPError, ValueError) as exc: 
        raise GeocodingError('Il servizio di geocodifica non è disponibile') from exc

    if not isinstance(payload, dict): 
        raise GeocodingError('Risposta di geocodifica non valida.')

    results = payload.get('results')
    if results is None or results == []:
        raise CityNotFoundError(f'Non trovo la città {city}')

    if not isinstance(results, list) or not isinstance(results[0], dict):
        raise GeocodingError('Risposta di geocodifica non valida.')

    result = results[0]
    try: 
        name = str(result['name'])
        latitute = float(result['latitude'])
        longitude = float(result['longitude'])
        timezone = str(result['timezone'])
        elevation_value = result.get('elevation')
        elevation_m = (float(elevation_value) if elevation_value is not None else None)
    except (KeyError, TypeError, ValueError) as exc: 
        raise GeocodingError('La risposta non contiene dati validi per la città') from exc

    return Location(
        name = name, 
        latitude = latitute, 
        longitude = longitude, 
        elevation_m = elevation_m,
        timezone = timezone,
    )