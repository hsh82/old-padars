(function () {
  const padars = (window.padars = window.padars || {});
  const schoolContext = (padars.school_context = {});

  function hasField(frm, fieldname) {
    return Boolean(frm && frm.fields_dict && frm.fields_dict[fieldname]);
  }

  function clearFields(frm, fields) {
    (fields || []).filter((fieldname) => hasField(frm, fieldname)).forEach((fieldname) => {
      if (frm.doc[fieldname]) frm.set_value(fieldname, null);
    });
  }

  function schoolFilters(frm, schoolField, additionalFilters) {
    const filters = Object.assign({}, additionalFilters || {});
    if (schoolField && frm.doc[schoolField]) filters.school = frm.doc[schoolField];
    return filters;
  }

  function resolveFilters(frm, filters) {
    return typeof filters === "function" ? filters(frm) || {} : filters || {};
  }

  schoolContext.hasField = hasField;
  schoolContext.clearFields = clearFields;
  schoolContext.schoolFilters = schoolFilters;

  schoolContext.setActiveSchoolQuery = function (frm, fieldname) {
    if (!hasField(frm, fieldname)) return;
    frm.set_query(fieldname, () => ({ filters: { status: "Active" } }));
  };

  schoolContext.setAcademicTermQuery = function (frm, academicYearField, termField) {
    if (!hasField(frm, termField) || !hasField(frm, academicYearField)) return;
    frm.set_query(termField, () => ({
      filters: { academic_year: frm.doc[academicYearField] || "" },
    }));
  };

  schoolContext.setProgramCourseQuery = function (frm, courseField, programField) {
    if (!hasField(frm, courseField) || !hasField(frm, programField)) return;
    frm.set_query(courseField, () => ({
      query: "education.education.doctype.program_enrollment.program_enrollment.get_program_courses",
      filters: { program: frm.doc[programField] || "" },
    }));
  };

  schoolContext.setSchoolStudentQuery = function (frm, studentField, schoolField, extraFilters) {
    if (!hasField(frm, studentField) || !hasField(frm, schoolField)) return;
    frm.set_query(studentField, () => ({
      query: "padars.api.get_school_students",
      filters: Object.assign({ school: frm.doc[schoolField] || "" }, resolveFilters(frm, extraFilters)),
    }));
  };

  schoolContext.setSchoolGridStudentQuery = function (
    frm,
    tableField,
    studentField,
    schoolField,
    extraFilters,
  ) {
    if (!hasField(frm, tableField) || !hasField(frm, schoolField)) return;
    const grid = frm.fields_dict[tableField].grid;
    if (!grid || !grid.get_field(studentField)) return;
    grid.get_field(studentField).get_query = () => ({
      query: "padars.api.get_school_students",
      filters: Object.assign({ school: frm.doc[schoolField] || "" }, resolveFilters(frm, extraFilters)),
    });
  };

  schoolContext.setSchoolInstructorQuery = function (frm, instructorField, schoolField) {
    if (!hasField(frm, instructorField) || !hasField(frm, schoolField)) return;
    frm.set_query(instructorField, () => ({
      query: "padars.api.get_school_instructors",
      filters: { school: frm.doc[schoolField] || "" },
    }));
  };

  schoolContext.setSchoolGridInstructorQuery = function (
    frm,
    tableField,
    instructorField,
    schoolField,
  ) {
    if (!hasField(frm, tableField) || !hasField(frm, schoolField)) return;
    const grid = frm.fields_dict[tableField].grid;
    if (!grid || !grid.get_field(instructorField)) return;
    grid.get_field(instructorField).get_query = () => ({
      query: "padars.api.get_school_instructors",
      filters: { school: frm.doc[schoolField] || "" },
    });
  };

  schoolContext.loadAuthorizedSchools = function (frm, schoolField, academicYearField) {
    if (!hasField(frm, schoolField)) return Promise.resolve([]);

    schoolContext.setActiveSchoolQuery(frm, schoolField);
    return frappe
      .call({ method: "padars.api.get_authorized_schools" })
      .then((response) => {
        const schools = response.message || [];
        frm.__padars_authorized_schools = schools;

        if (!frm.doc[schoolField] && schools.length === 1) {
          frm.set_value(schoolField, schools[0].name);
        }

        const selected = schools.find((school) => school.name === frm.doc[schoolField]);
        if (selected && academicYearField && hasField(frm, academicYearField)) {
          if (!frm.doc[academicYearField] && selected.current_academic_year) {
            frm.set_value(academicYearField, selected.current_academic_year);
          }
        }
        return schools;
      })
      .catch(() => []);
  };

  schoolContext.setSchoolYearFromContext = function (frm, schoolField, academicYearField) {
    if (!hasField(frm, schoolField) || !hasField(frm, academicYearField)) return;
    const school = (frm.__padars_authorized_schools || []).find(
      (item) => item.name === frm.doc[schoolField],
    );
    if (school && school.current_academic_year) {
      frm.set_value(academicYearField, school.current_academic_year);
    }
  };
})();
