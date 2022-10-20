# Copyright (c) 2022, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from gameplan.gameplan.doctype.team_discussion.search import DiscussionsSearchIndex
from gameplan.mixins.mentions import HasMentions
from gameplan.mixins.reactions import HasReactions
from frappe.utils import cstr, strip_html_tags

class TeamComment(HasMentions, HasReactions, Document):
	on_delete_set_null = ["Team Notification"]
	mentions_field = 'content'

	def before_insert(self):
		if self.reference_doctype not in ["Team Discussion"]:
			return

		reference_doc = frappe.get_doc(self.reference_doctype, self.reference_name)
		if reference_doc.meta.has_field("closed_at"):
			if reference_doc.closed_at:
				frappe.throw("Cannot add comment to a closed discussion")

	def after_insert(self):
		if self.reference_doctype not in ["Team Discussion", "Team Task"]:
			return
		reference_doc = frappe.get_doc(self.reference_doctype, self.reference_name)
		if reference_doc.meta.has_field("last_post_at"):
			reference_doc.set("last_post_at", frappe.utils.now())
		if reference_doc.meta.has_field("last_post_by"):
			reference_doc.set("last_post_by", frappe.session.user)
		if reference_doc.meta.has_field("comments_count"):
			reference_doc.set("comments_count", reference_doc.comments_count + 1)
		reference_doc.save(ignore_permissions=True)

	def on_trash(self):
		if self.reference_doctype not in ["Team Discussion", "Team Task"]:
			return
		reference_doc = frappe.get_doc(self.reference_doctype, self.reference_name)
		if reference_doc.meta.has_field("comments_count"):
			reference_doc.db_set("comments_count", reference_doc.comments_count - 1)

	def on_update(self):
		self.update_discussion_index()
		self.notify_mentions()
		self.notify_reactions()

	def update_discussion_index(self):
		d = DiscussionsSearchIndex()
		if self.reference_doctype == "Team Discussion":
			if self.deleted_at:
				record = frappe._dict({
					'name': self.reference_name,
					'comment': self.name
				})
				d.remove_index_for_records([record])
			else:
				record = frappe._dict({
					'name': self.reference_name,
					'title': '',
					'content': strip_html_tags(self.content),
					'modified': cstr(self.modified),
					'comment': self.name
				})
				d.create_index_for_records([record])
