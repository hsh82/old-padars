from typing import Protocol


class MoodleAdapter(Protocol):
	name: str

	def ensure_tenant(self, school):
		"""Create or reconcile a remote tenant for a local School."""

	def ensure_user(self, user, school, tenant=None):
		"""Create or reconcile a remote user in a local School tenant."""

	def create_course(self, offering):
		"""Create or reconcile a remote course for a local School Course Offering."""

	def sync_enrollment(self, enrollment_state, remote_user, remote_course):
		"""Reconcile one desired enrollment state in the remote LMS."""


	def read_grade_items(self, school, course_mapping, user_mapping):
		"""Read one mapped user's grade items after verifying tenant context."""
