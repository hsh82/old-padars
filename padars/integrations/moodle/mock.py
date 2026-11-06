import hashlib


class MockMoodleAdapter:
	name = "Mock"

	def health_check(self):
		return {"sitename": "Mock Moodle", "release": "mock", "username": "padars-test", "userid": 1}

	def ensure_tenant(self, school):
		key = hashlib.sha256(school.name.encode()).hexdigest()[:20]
		return {
			"remote_type": "Moodle Tenant",
			"remote_id": "mock-tenant-" + key,
			"remote_context": f"mock-tenant:{school.name}",
			"remote_url": f"https://mock.invalid/tenant/{key}",
			"tenant_name": school.school_name,
			"tenant_idnumber": "padars" + key,
			"category_id": "mock-category-" + key,
			"cohort_id": "mock-cohort-" + key,
			"associated_cohort_id": "mock-associated-cohort-" + key,
		}

	def ensure_user(self, user, school, tenant=None):
		return {
			"remote_type": "Moodle User",
			"remote_id": "mock-user-" + hashlib.sha256(user.name.encode()).hexdigest()[:20],
			"remote_context": f"mock-tenant:{school.name}",
			"remote_url": "https://mock.invalid/user/" + hashlib.sha256(user.name.encode()).hexdigest()[:20],
		}

	def create_course(self, offering):
		remote_id = "mock-course-" + hashlib.sha256(offering.name.encode()).hexdigest()[:20]
		return {
			"remote_type": "Moodle Course",
			"remote_id": remote_id,
			"remote_context": f"mock-tenant:{offering.school}",
			"url": "",
			"remote_url": f"https://mock.invalid/course/{remote_id}",
		}

	def sync_enrollment(self, enrollment_state, remote_user=None, remote_course=None):
		key = f"{enrollment_state.user}:{enrollment_state.course_offering}:{enrollment_state.role}"
		course_id = remote_course["remote_id"] if remote_course else hashlib.sha256(key.encode()).hexdigest()[:20]
		user_id = remote_user["remote_id"] if remote_user else hashlib.sha256(key.encode()).hexdigest()[:20]
		return {
			"remote_type": "Moodle Enrollment",
			"remote_id": f"mock-enrollment-{course_id}-{user_id}",
			"remote_context": f"mock-tenant:{enrollment_state.school}",
			"remote_url": remote_course.get("remote_url") if remote_course else "",
			"remote_state": enrollment_state.desired_state,
		}


	def read_grade_items(self, school, course_mapping, user_mapping):
		# No synthetic grades are invented for school records.
		return []

	def read_course_activities(self, school, course_mapping):
		return []

	def read_activity_completions(self, school, course_mapping, user_mapping):
		return []
