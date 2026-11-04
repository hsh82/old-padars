import hashlib


class MockMoodleAdapter:
	name = "Mock"

	def ensure_tenant(self, school):
		return {
			"remote_type": "Moodle Tenant",
			"remote_id": "mock-tenant-" + hashlib.sha256(school.name.encode()).hexdigest()[:20],
			"remote_context": f"mock-tenant:{school.name}",
		}

	def ensure_user(self, user, school):
		return {
			"remote_type": "Moodle User",
			"remote_id": "mock-user-" + hashlib.sha256(user.name.encode()).hexdigest()[:20],
			"remote_context": f"mock-tenant:{school.name}",
		}

	def create_course(self, offering):
		remote_id = "mock-course-" + hashlib.sha256(offering.name.encode()).hexdigest()[:20]
		return {
			"remote_type": "Moodle Course",
			"remote_id": remote_id,
			"remote_context": f"mock-tenant:{offering.school}",
			"url": "",
		}

	def sync_enrollment(self, enrollment_state):
		key = f"{enrollment_state.user}:{enrollment_state.course_offering}:{enrollment_state.role}"
		return {
			"remote_type": "Moodle Enrollment",
			"remote_id": "mock-enrollment-" + hashlib.sha256(key.encode()).hexdigest()[:20],
			"remote_context": f"mock-tenant:{enrollment_state.school}",
			"remote_state": enrollment_state.desired_state,
		}

