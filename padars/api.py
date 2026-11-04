import frappe

from padars.integrations.moodle.service import (
	request_course_offering_sync as create_course_offering_sync,
	retry_sync_operation as retry_operation,
)


@frappe.whitelist()
def request_course_offering_sync(course_offering):
	offering = frappe.get_doc("School Course Offering", course_offering)
	offering.check_permission("read")
	operation = create_course_offering_sync(offering)
	return operation.as_dict()


@frappe.whitelist()
def retry_sync_operation(operation):
	operation_doc = frappe.get_doc("LMS Sync Operation", operation)
	operation_doc.check_permission("write")
	return retry_operation(operation_doc.name).as_dict()

