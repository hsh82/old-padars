"""Integrity checks for Education's official assessment results."""

import math

import frappe
from frappe import _


def validate_result_scores(doc, method=None):
	"""Use the plan's criteria and maxima as the sole basis for entered scores."""
	if not doc.assessment_plan:
		frappe.throw(_("Choose an Assessment Plan before entering scores."))
	criteria = frappe.get_all("Assessment Plan Criteria", filters={
		"parent": doc.assessment_plan, "parenttype": "Assessment Plan", "parentfield": "assessment_criteria",
	}, fields=["assessment_criteria", "maximum_score"])
	maxima = {}
	for row in criteria:
		maximum = float(row.maximum_score or 0)
		if not row.assessment_criteria or row.assessment_criteria in maxima or not math.isfinite(maximum) or maximum <= 0:
			frappe.throw(_("The Assessment Plan must have unique criteria with positive finite maximum scores."))
		maxima[row.assessment_criteria] = maximum
	if not maxima:
		frappe.throw(_("The Assessment Plan must contain assessment criteria."))
	seen = set()
	for row in doc.details:
		criterion = row.assessment_criteria
		if criterion not in maxima or criterion in seen:
			frappe.throw(_("Each Assessment Result criterion must appear exactly once in its Assessment Plan."))
		seen.add(criterion)
		score = float(row.score or 0)
		if not math.isfinite(score) or score < 0 or score > maxima[criterion]:
			frappe.throw(_("Scores must be between zero and the criterion maximum."))
	if seen != set(maxima):
		frappe.throw(_("Enter a score for each Assessment Plan criterion."))
	doc.maximum_score = sum(maxima.values())
