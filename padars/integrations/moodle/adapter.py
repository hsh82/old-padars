from typing import Protocol


class MoodleAdapter(Protocol):
	def ensure_tenant(self, school):
		"""Create or reconcile a remote tenant for a local School."""

	def ensure_user(self, user, school):
		"""Create or reconcile a remote user in a local School tenant."""

	def create_course(self, offering):
		"""Create or reconcile a remote course for a local School Course Offering."""

	def sync_enrollment(self, enrollment_state):
		"""Reconcile one desired enrollment state in the remote LMS."""

