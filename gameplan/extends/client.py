# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.base_document import get_controller


@frappe.whitelist()
def get_list(doctype=None, fields=None, filters=None, order_by=None, start=0, limit=20, parent=None, debug=False):
	check_permissions(doctype, parent)
	query = frappe.qb.engine.get_query(
		table=doctype,
		fields=fields,
		filters=filters,
		order_by=order_by,
		start=start,
		limit=limit,
		parent=parent
	)
	if order_by:
		for declaration in order_by.split(','):
			parts = declaration.strip().split(" ")
			orderby_field = parts[0]
			orderby_direction = parts[1] if len(parts) > 1 else "asc"
			query = query.orderby(orderby_field, order=frappe._dict(value=orderby_direction))

	query = apply_custom_filters(doctype, query)
	return query.run(as_dict=True, debug=debug)

def check_permissions(doctype, parent):
	user = frappe.session.user
	if (
		not frappe.has_permission(doctype, "select", user=user, parent_doctype=parent)
		and not frappe.has_permission(doctype, "read", user=user, parent_doctype=parent)
	):
		frappe.throw(f'Insufficient Permission for {doctype}', frappe.PermissionError)

def apply_custom_filters(doctype, query):
	"""Apply custom filters to query"""
	controller = get_controller(doctype)
	if hasattr(controller, "get_list_query"):
		return_value = controller.get_list_query(query)
		if return_value is not None:
			query = return_value

	return query

@frappe.whitelist()
def batch(requests):
	from frappe.handler import handle
	from frappe.app import handle_exception
	requests = frappe.parse_json(requests)
	responses = []

	for i, request_params in enumerate(requests):
		savepoint = f'batch_request_{i}'
		try:
			frappe.db.savepoint(savepoint)
			frappe.form_dict.update(request_params)
			response = handle()
			frappe.db.release_savepoint(savepoint)
		except Exception as e:
			frappe.db.rollback(save_point=savepoint)
			response = handle_exception(e)

		responses.append(response)

	return [r.json for r in responses]
