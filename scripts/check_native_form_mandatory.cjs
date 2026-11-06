// Execute the installed Frappe mandatory checker in a small Desk-data harness.
// This verifies metadata behavior; it does not replace browser interaction tests.
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const root = path.resolve(__dirname, "..");
const index = process.argv.indexOf("--frappe-root");
if (index < 0 || !process.argv[index + 1]) throw new Error("Pass --frappe-root <installed Frappe app>");
const nativeSource = fs.readFileSync(path.join(process.argv[index + 1], "frappe/public/js/frappe/form/save.js"), "utf8");
for (const folder of ["school_assessment_scheme", "moodle_grade_mapping", "session_attendance_policy"]) {
	const meta = JSON.parse(fs.readFileSync(path.join(root, "padars/padars/doctype", folder, `${folder}.json`), "utf8"));
	const computed = meta.fields.filter((field) => field.read_only && field.reqd);
	assert(computed.length > 0);
	let fields = structuredClone(meta.fields);
	const doc = {doctype: meta.name, name: "new-test", __islocal: 1, docstatus: 0};
	for (const field of fields.filter((field) => field.reqd && !field.read_only)) doc[field.fieldname] = field.default ?? "configured";
	const editable = fields.find((field) => field.reqd && !field.read_only);
	let messages = 0;
	const frappe = {
		ui: {form: {}},
		model: {get_all_docs: () => [doc], has_value: (_dt, _name, field) => ![undefined, null, ""].includes(doc[field])},
		meta: {docfield_list: {[meta.name]: fields}, get_docfield_copy: () => Object.fromEntries(fields.map((field) => [field.fieldname, field]))},
		get_meta: () => meta, msgprint: () => { messages++; },
		utils: {eval: (expression, context) => vm.runInNewContext(expression, context)},
	};
	const $ = {each: (values, callback) => Array.isArray(values) ? values.forEach((value, key) => callback(key, value)) : Object.entries(values).forEach(([key, value]) => callback(key, value)), isArray: Array.isArray};
	vm.runInNewContext(nativeSource, {frappe, $, __: (text) => text});
	const frm = {doc, meta, is_new: () => !!doc.__islocal, layout: {}, scroll_to_field() {}, refresh() {}};
	assert.equal(frappe.ui.form.check_mandatory(frm), true, `${meta.name}: new form blocked by generated fields`);
	const value = doc[editable.fieldname];
	delete doc[editable.fieldname];
	assert.equal(frappe.ui.form.check_mandatory(frm), false, `${meta.name}: missing editable field was accepted`);
	assert(messages > 0);
	doc[editable.fieldname] = value;
	// Reproduce the pre-fix behavior using exactly the same installed checker.
	fields.find((field) => field.fieldname === computed[0].fieldname).mandatory_depends_on = null;
	assert.equal(frappe.ui.form.check_mandatory(frm), false, `${meta.name}: original blocking metadata did not reproduce`);
	console.log(`PASS: ${meta.name}: native new-form validation, missing-input denial and original-failure reproduction`);
}
