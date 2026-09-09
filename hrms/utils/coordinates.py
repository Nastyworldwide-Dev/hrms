"""Chinese map coordinates to the WGS-84 that every phone reports.

Map services inside mainland China publish positions in GCJ-02 (Google
China, Amap, Tencent) or BD-09 (Baidu). A pin copied from one of them sits
100 to 700 m from where a phone's GPS says the same building is, so every
punch reads outside a 100 m radius. On 9 September 2026 an office in
mainland China had exactly this: staff inside, "outside the radius" every
day.

The transform is the published one (the "Krasovsky 1940 / offset" algorithm
used by every open converter); accurate to a few metres, which is far below
any check-in radius. Pure Python, no frappe import.
"""

import logging
import math

logger = logging.getLogger(__name__)

WGS84 = "WGS-84"
GCJ02 = "GCJ-02"
BD09 = "BD-09"
COORDINATE_SYSTEMS = (WGS84, GCJ02, BD09)

_A = 6378245.0
_EE = 0.00669342162296594323
_X_PI = math.pi * 3000.0 / 180.0


def _out_of_china(lat, lng):
	return not (73.66 < lng < 135.05 and 3.86 < lat < 53.55)


def _transform_lat(x, y):
	ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
	ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
	ret += (20.0 * math.sin(y * math.pi) + 40.0 * math.sin(y / 3.0 * math.pi)) * 2.0 / 3.0
	ret += (160.0 * math.sin(y / 12.0 * math.pi) + 320 * math.sin(y * math.pi / 30.0)) * 2.0 / 3.0
	return ret


def _transform_lng(x, y):
	ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
	ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
	ret += (20.0 * math.sin(x * math.pi) + 40.0 * math.sin(x / 3.0 * math.pi)) * 2.0 / 3.0
	ret += (150.0 * math.sin(x / 12.0 * math.pi) + 300.0 * math.sin(x / 30.0 * math.pi)) * 2.0 / 3.0
	return ret


def wgs84_to_gcj02(lat, lng):
	if _out_of_china(lat, lng):
		return lat, lng
	dlat = _transform_lat(lng - 105.0, lat - 35.0)
	dlng = _transform_lng(lng - 105.0, lat - 35.0)
	radlat = lat / 180.0 * math.pi
	magic = math.sin(radlat)
	magic = 1 - _EE * magic * magic
	sqrtmagic = math.sqrt(magic)
	dlat = (dlat * 180.0) / ((_A * (1 - _EE)) / (magic * sqrtmagic) * math.pi)
	dlng = (dlng * 180.0) / (_A / sqrtmagic * math.cos(radlat) * math.pi)
	return lat + dlat, lng + dlng


def gcj02_to_wgs84(lat, lng):
	"""Invert the offset by one correction step: accurate to a few metres."""
	if _out_of_china(lat, lng):
		return lat, lng
	glat, glng = wgs84_to_gcj02(lat, lng)
	return lat * 2 - glat, lng * 2 - glng


def bd09_to_gcj02(lat, lng):
	x, y = lng - 0.0065, lat - 0.006
	z = math.sqrt(x * x + y * y) - 0.00002 * math.sin(y * _X_PI)
	theta = math.atan2(y, x) - 0.000003 * math.cos(x * _X_PI)
	return z * math.sin(theta), z * math.cos(theta)


def to_wgs84(lat, lng, system):
	"""Coordinates as a phone reports them, whatever map they were read from."""
	lat, lng = float(lat), float(lng)
	if system == BD09:
		lat, lng = bd09_to_gcj02(lat, lng)
		system = GCJ02
	if system == GCJ02:
		lat, lng = gcj02_to_wgs84(lat, lng)
	elif system not in (WGS84, None, ""):
		raise ValueError(f"unknown coordinate system: {system}")
	logger.info("[coordinates] converted from %s to WGS-84", system or WGS84)
	return round(lat, 7), round(lng, 7)
