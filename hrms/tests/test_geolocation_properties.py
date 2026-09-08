"""Generated cross-language contract checks; no browser, site, DB or new dependency.

Python's production geofence decision is the preview oracle. Browser fix
validation is checked separately, before any decision can use those coordinates.
"""

import json
import subprocess
import unittest
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from hrms.utils.geofence import evaluate_geofence, parse_coordinates

ROOT = Path(__file__).resolve().parents[2]
JS = """
import { readFileSync } from 'node:fs';
import { previewGeofence, usablePosition, validCoordinates } from './frontend/src/utils/geolocation.js';
console.debug = console.warn = () => {};
const request = JSON.parse(readFileSync(0, 'utf8'));
const output = request.cases.map(row => {
 if (request.kind === 'preview') {
  const result = previewGeofence(row);
  return [result.action, result.action === 'allow' ? null : result.reason];
 }
 if (request.kind === 'coordinates') return validCoordinates(row[0], row[1]);
 return usablePosition(row.position, row.now) !== null;
});
process.stdout.write(JSON.stringify(output));
"""


def javascript(kind, cases):
	result = subprocess.run(
		["node", "--input-type=module", "-e", JS],
		cwd=ROOT,
		input=json.dumps({"kind": kind, "cases": cases}, allow_nan=False),
		capture_output=True,
		text=True,
		check=True,
		timeout=10,
	)
	return json.loads(result.stdout)


def server_decision(case):
	result = evaluate_geofence(
		case["strict"], case["hasLocation"], case["radius"], case["distance"], case["accuracy"]
	)
	return [result[0], result[1]["reason"]] if result else ["allow", None]


class TestPreviewParity(unittest.TestCase):
	def test_exact_server_policy_boundaries(self):
		cases = [
			dict(strict=strict, hasLocation=has_location, radius=radius, distance=distance, accuracy=accuracy)
			for strict in (False, True)
			for has_location in (False, True)
			for radius in (0, 100)
			for distance in (None, 0, 100, 120, 1300)
			for accuracy in (None, 0, 40, 250, 251, 1500, 2000, 2001, 5000)
		]
		self.assertEqual(javascript("preview", cases), [server_decision(row) for row in cases])

	@settings(max_examples=40, deadline=None)
	@given(
		strict=st.booleans(),
		radius=st.integers(min_value=0, max_value=500),
		distance=st.floats(min_value=0, max_value=10000, allow_nan=False, allow_infinity=False),
		accuracy=st.one_of(
			st.none(), st.floats(min_value=0, max_value=10000, allow_nan=False, allow_infinity=False)
		),
	)
	def test_generated_geofence_matches_authoritative_decision(self, strict, radius, distance, accuracy):
		case = dict(strict=strict, hasLocation=True, radius=radius, distance=distance, accuracy=accuracy)
		self.assertEqual(javascript("preview", [case]), [server_decision(case)])

	@settings(max_examples=40, deadline=None)
	@given(
		latitude=st.one_of(
			st.none(),
			st.booleans(),
			st.floats(min_value=-200, max_value=200, allow_nan=False, allow_infinity=False),
		),
		longitude=st.one_of(
			st.none(),
			st.booleans(),
			st.floats(min_value=-300, max_value=300, allow_nan=False, allow_infinity=False),
		),
	)
	def test_coordinate_acceptance_matches_server_finite_range_boundary(self, latitude, longitude):
		self.assertEqual(
			javascript("coordinates", [[latitude, longitude]]),
			[parse_coordinates(latitude, longitude) is not None],
		)

	@settings(max_examples=40, deadline=None)
	@given(
		age=st.integers(min_value=-120000, max_value=300000),
		accuracy=st.one_of(
			st.none(), st.floats(min_value=-1000, max_value=10000, allow_nan=False, allow_infinity=False)
		),
	)
	def test_only_current_nonnegative_accuracy_readings_can_be_used(self, age, accuracy):
		now = 1800000000000
		case = {
			"position": {
				"coords": {"latitude": 0, "longitude": 0, "accuracy": accuracy},
				"timestamp": now - age,
			},
			"now": now,
		}
		self.assertEqual(
			javascript("fix", [case]), [0 <= age <= 60000 and (accuracy is None or accuracy >= 0)]
		)
