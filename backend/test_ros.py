#!/usr/bin/env python3

from api_service import fetch_environmental_data
from mock_engine import _rothermel_spread_rate

env = fetch_environmental_data(-7.6167, 40.3217)
print('=== Environmental Data ===')
print(f'Slope: {env["slope_deg"]}°')
print(f'Fuel type: {env["fuel_type"]}')
print(f'Wind: {env["weather"]["wind_speed_ms"]} m/s')
print(f'Humidity: {env["weather"]["relative_humidity_pct"]}%')
print()

ros = _rothermel_spread_rate(
    wind_speed_ms=env['weather']['wind_speed_ms'],
    slope_deg=env['slope_deg'],
    fuel_data=env['fuel'],
    temperature_c=env['weather']['temperature_c'],
    relative_humidity_pct=env['weather']['relative_humidity_pct']
)
print(f'Spread rate: {ros:.2f} m/min')
print(f'Distance in 10 min: {ros * 10:.1f} m')
print(f'Distance in 60 min: {ros * 60:.1f} m')
