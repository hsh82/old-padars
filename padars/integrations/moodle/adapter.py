from typing import Protocol


class MoodleAdapter(Protocol):
	def create_course(self, offering):
		"""Create or reconcile a remote course for a local School Course Offering."""

