import webnotes
def execute():
	"""
		* Custom Field changes
		* Add file_list to required tables
		* Change floats/currency to decimal(14, 6)
		* Remove DocFormat from DocType's fields
		* Remove 'no_column' from DocField
		* Drop table DocFormat
	"""
	handle_custom_fields()
	create_file_list()

	# do at last - needs commit due to DDL statements
	change_to_decimal()

def handle_custom_fields():
	"""
		* Assign idx to custom fields
		* Create property setter entry of previous field
		* Remove custom fields from tabDocField
	"""
	cf = get_cf()
	assign_idx(cf)
	create_prev_field_prop_setter(cf)
	remove_custom_from_docfield(cf)

def get_cf():
	return webnotes.conn.sql("""\
		SELECT * FROM `tabCustom Field`
		WHERE docstatus < 2""", as_dict=1)

def assign_idx(cf):
	from webnotes.model.doctype import get
	from webnotes.utils import cint
	for f in cf:
		if f.get('idx'): continue
		temp_doclist = get(f.get('dt'), form=0)
		max_idx = max(d.idx for d in temp_doclist if d.doctype=='DocField')
		if not max_idx: continue
		webnotes.conn.sql("""\
			UPDATE `tabCustom Field` SET idx=%s
			WHERE name=%s""", (cint(max_idx)+1, f.get('name')))

def create_prev_field_prop_setter(cf):
	from webnotes.model.doc import Document
	from core.doctype.custom_field.custom_field import get_fields_label
	for f in cf:
		idx_label_list, field_list = get_fields_label(f.get('dt'), 0)
		temp_insert_after = (f.get('insert_after') or '').split(" - ")
		if len(temp_insert_after)<=1: continue
		similar_idx_label = [il for il in idx_label_list \
			if temp_insert_after[0] in il]
		if not similar_idx_label: continue
		label_index = idx_label_list.index(similar_idx_label[0])
		if label_index==-1: return

		webnotes.conn.sql("""\
			UPDATE `tabCustom Field`
			SET insert_after = %s
			WHERE name = %s""", (similar_idx_label[0], f.get('name')))

		prev_field = field_list[label_index]
		webnotes.conn.sql("""\
			DELETE FROM `tabProperty Setter`
			WHERE doc_type = %s
			AND doc_name = %s
			AND property = 'previous_field'""", (f.get('dt'), f.get('name')))
		ps = Document('Property Setter', fielddata = {
			'doctype_or_field': 'DocField',
			'doc_type': f.get('dt'),
			'doc_name': f.get('name'),
			'property': 'previous_field',
			'value': prev_field,
			'property_type': 'Data',
			'select_doctype': f.get('dt')
		})
		ps.save(1)

def remove_custom_from_docfield(cf):
	for f in cf:
		webnotes.conn.sql("""\
			DELETE FROM `tabDocField`
			WHERE parent=%s AND fieldname=%s""", (f.get('dt'),
			f.get('fieldname')))

def create_file_list():
	tables = webnotes.conn.sql("SHOW TABLES")
	exists = []
	for tab in tables:
		if not tab: continue
		desc = webnotes.conn.sql("DESC `%s`" % tab[0], as_dict=1)

		for d in desc:
			if d.get('Field')=='file_list':
				exists.append(tab[0])
				break
	
	print exists
	
	should_exist = ['Website Settings', 'Web Page', 'Timesheet', 'Ticket',
		'Support Ticket', 'Supplier', 'Style Settings', 'Stock Reconciliation',
		'Stock Entry', 'Serial No', 'Sales Order', 'Receivable Voucher',
		'Quotation', 'Question', 'Purchase Receipt', 'Purchase Order',
		'Project', 'Profile', 'Production Order', 'Product', 'Print Format',
		'Price List', 'Payable Voucher', 'Page', 'Module Def',
		'Maintenance Visit', 'Maintenance Schedule', 'Letter Head',
		'Leave Application', 'Lead', 'Journal Voucher', 'Item', 'Indent',
		'Expense Voucher', 'Enquiry', 'Employee', 'Delivery Note',
		'Customer Issue', 'Customer', 'Contact Us Settings', 'Company',
		'Bulk Rename Tool', 'Blog', 'Bill Of Materials', 'About Us Settings']

	from webnotes.model.code import get_obj

	for dt in should_exist:
		if dt in exists: continue
		obj = get_obj('DocType', dt, with_children=1)
		obj.doc.allow_attach = 1
		obj.doc.save()
		obj.make_file_list()
		obj.on_update()


def change_to_decimal():
	webnotes.conn.commit()
	tables = webnotes.conn.sql("SHOW TABLES")
	alter_tables_list = []
	for tab in tables:
		if not tab: continue
		desc = webnotes.conn.sql("DESC `%s`" % tab[0], as_dict=1)
		flist = []
		for d in desc:
			if d.get('Type')=='decimal(14,2)':
				flist.append(d.get('Field'))
		if flist:
			#print tab[0], flist
			statements = ("MODIFY `%s` decimal(14,6)" % f for f in flist)
			statements = ", \n".join(statements)
			alter_tables_list.append("ALTER TABLE `%s` \n%s\n" % (tab[0],
				statements))
	
	#print "\n\n".join(alter_tables_list)
	for at in alter_tables_list:
		webnotes.conn.sql(at)

	webnotes.conn.begin()

