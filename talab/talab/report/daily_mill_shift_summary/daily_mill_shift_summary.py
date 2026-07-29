import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}
	conditions, values = ["docstatus < 2"], {}
	for fieldname in ("mill", "customer", "shift_status", "payment_status"):
		if filters.get(fieldname):
			conditions.append(f"{fieldname} = %({fieldname})s")
			values[fieldname] = filters[fieldname]
	if filters.get("from_date"):
		conditions.append("shift_date >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("shift_date <= %(to_date)s")
		values["to_date"] = filters["to_date"]
	columns = [
		_("Date") + ":Date:100",
		_("Mill") + ":Link/Talab Mill:130",
		_("Shift Number") + ":Int:90",
		_("Customer") + ":Link/Customer:150",
		_("Opening Time") + ":Datetime:150",
		_("Closing Time") + ":Datetime:150",
		_("Issued Mercury") + ":Float:110",
		_("Returned Mercury") + ":Float:120",
		_("Shortage") + ":Float:100",
		_("Exemption") + ":Float:100",
		_("Chargeable Mercury") + ":Float:140",
		_("Rental Amount") + ":Currency:120",
		_("Mercury Charge") + ":Currency:120",
		_("Total Due") + ":Currency:110",
		_("Amount Paid") + ":Currency:120",
		_("Outstanding Amount") + ":Currency:140",
		_("Status") + ":Data:100",
	]
	data = frappe.db.sql(
		"""SELECT shift_date, mill, shift_number, customer, opening_datetime, closing_datetime,
		mercury_issued, mercury_returned, mercury_shortage, mercury_exemption, chargeable_mercury,
		shift_rental_amount, mercury_charge, total_due, amount_paid, outstanding_amount, shift_status
		FROM `tabTalab Mill Shift` WHERE {} ORDER BY shift_date DESC, mill, shift_number""".format(" AND ".join(conditions)),
		values,
	)
	return columns, data
