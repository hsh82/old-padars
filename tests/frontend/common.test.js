const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const appRoot = path.resolve(__dirname, "../..");

function loadBrowserScript(relativePath) {
	const context = {
		window: {},
		frappe: {},
		__: (value) => value,
	};
	vm.runInNewContext(
		fs.readFileSync(path.join(appRoot, relativePath), "utf8"),
		context,
		{ filename: relativePath },
	);
	return context.window.padars;
}

test("school context clears dependent fields and tolerates incomplete grids", () => {
	const schoolContext = loadBrowserScript("padars/public/js/common/school_context.js").school_context;
	const frm = {
		fields_dict: { school: {}, academic_year: {}, students: { grid: { get_field: () => null } } },
		doc: { school: "SCHOOL-001", academic_year: "2026" },
		set_value(fieldname, value) {
			this.doc[fieldname] = value;
		},
	};

	schoolContext.clearFields(frm, ["academic_year"]);
	assert.equal(frm.doc.academic_year, null);
	assert.doesNotThrow(() => {
		schoolContext.setSchoolGridStudentQuery(frm, "students", "student", "school");
	});

	const query = schoolContext.schoolFilters;
	const filters = query(frm, "school", { academic_year: "2026" });
	assert.equal(filters.school, "SCHOOL-001");
	assert.equal(filters.academic_year, "2026");
});

test("LMS helper normalizes states and limits error text", () => {
	const lms = loadBrowserScript("padars/public/js/common/lms_sync.js").lms;
	assert.equal(lms.labelForState("Succeeded"), "Successful");
	assert.equal(lms.statusClass("Failed"), "failed");
	assert.equal(lms.indicatorColor("Running"), "blue");
	assert.equal(lms.safeError("  first\nsecond  "), "first second");
	assert.equal(lms.safeError("x".repeat(300)).length, 240);
});
