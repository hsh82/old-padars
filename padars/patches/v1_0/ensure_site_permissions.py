from padars.install import ensure_academic_permissions, ensure_stage1_roles


def execute():
	ensure_stage1_roles()
	ensure_academic_permissions()
