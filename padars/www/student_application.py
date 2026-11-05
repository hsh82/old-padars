from padars.student_activation import _sms_required


def get_context(context):
	context.sms_required = _sms_required()
	context.no_cache = 1
