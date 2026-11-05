"""Prevent Frappe error snapshots from retaining registration credentials."""

from functools import wraps

import frappe
from frappe import _


def protect_registration_request(fn):
	@wraps(fn)
	def protected(*args, **kwargs):
		try:
			return fn(*args, **kwargs)
		except Exception:
			if not getattr(frappe.local, "request", None):
				raise
			frappe.db.rollback()
			frappe.clear_messages()
			for key in ("national_id", "phone", "email", "temporary_password", "new_password",
				"confirm_password", "otp", "status_token"):
				frappe.form_dict.pop(key, None)
			frappe.flags.disable_traceback = True
			# Frappe excludes AuthenticationError from error snapshots. Do not
			# attach the original exception or request credentials to the response.
			raise frappe.AuthenticationError(_("Unable to complete the request. Contact the school if needed.")) from None
	return protected
