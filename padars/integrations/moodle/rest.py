"""Small, server-side Moodle REST client.

The token is sent only in a POST body. Request and response bodies are never
logged or copied into operation diagnostics.
"""

from urllib.parse import urlsplit

import requests


class MoodleAPIError(Exception):
	"""A redacted failure returned by Moodle or the HTTP transport."""


def validate_moodle_base_url(value, allowed_hosts):
	parsed = urlsplit((value or "").strip())
	host = (parsed.hostname or "").lower().rstrip(".")
	if isinstance(allowed_hosts, str):
		allowed_hosts = allowed_hosts.split(",")
	allowed = {str(item).strip().lower().rstrip(".") for item in (allowed_hosts or []) if item}
	try:
		port = parsed.port
	except ValueError as exc:
		raise ValueError("The Moodle URL contains an invalid port.") from exc
	if (
		parsed.scheme != "https"
		or not host
		or parsed.username
		or parsed.password
		or parsed.query
		or parsed.fragment
		or host not in allowed
		or host == "localhost"
		or host.endswith((".localhost", ".local", ".internal"))
	):
		raise ValueError("The Moodle URL must use HTTPS and match a server-configured allowed host.")
	if port not in (None, 443):
		raise ValueError("The Moodle URL must use the standard HTTPS port.")
	path = parsed.path.rstrip("/")
	return f"https://{host}{path}"


def _form_data(value, prefix=""):
	"""Flatten Moodle's nested REST parameters into PHP form field names."""
	data = {}
	if isinstance(value, dict):
		for key, child in value.items():
			name = f"{prefix}[{key}]" if prefix else str(key)
			data.update(_form_data(child, name))
	elif isinstance(value, (list, tuple)):
		for index, child in enumerate(value):
			name = f"{prefix}[{index}]"
			data.update(_form_data(child, name))
	else:
		data[prefix] = "" if value is None else ("1" if value is True else "0" if value is False else str(value))
	return data


class MoodleRESTClient:
	def __init__(self, base_url, token, timeout=20, session=None):
		self.base_url = base_url.rstrip("/")
		self.token = token
		self.timeout = int(timeout or 20)
		self.session = session or requests.Session()

	def call(self, function, params=None):
		form = {
			"wstoken": self.token,
			"wsfunction": function,
			"moodlewsrestformat": "json",
			**_form_data(params or {}),
		}
		try:
			response = self.session.post(
				f"{self.base_url}/webservice/rest/server.php",
				data=form,
				timeout=self.timeout,
				verify=True,
				allow_redirects=False,
				headers={"Accept": "application/json"},
			)
		except requests.Timeout as exc:
			raise MoodleAPIError("Moodle request timed out.") from exc
		except requests.RequestException as exc:
			raise MoodleAPIError("Moodle connection failed.") from exc

		if not 200 <= response.status_code < 300:
			raise MoodleAPIError(f"Moodle returned HTTP {response.status_code}.")
		try:
			result = response.json()
		except (ValueError, requests.JSONDecodeError) as exc:
			raise MoodleAPIError("Moodle returned an unreadable response.") from exc
		if isinstance(result, dict) and result.get("exception"):
			code = str(result.get("errorcode") or "remote_error")[:80]
			raise MoodleAPIError(f"Moodle rejected the request ({code}).")
		return result
