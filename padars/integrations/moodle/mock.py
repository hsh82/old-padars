import hashlib


class MockMoodleAdapter:
	name = "Mock"

	def create_course(self, offering):
		remote_id = "mock-course-" + hashlib.sha256(offering.name.encode()).hexdigest()[:20]
		return {
			"remote_type": "Moodle Course",
			"remote_id": remote_id,
			"remote_context": f"mock-school:{offering.school}",
			"url": "",
		}

