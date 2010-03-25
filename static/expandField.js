goog.provide('cr.expandField')

goog.require('goog.dom')

cr.expandField.expandFields = []

cr.expandField.toggleExpandField = function(id) {
	var field = goog.dom.$('expandField_' + id)
	
	var newValue = cr.expandField.expandFields[id]
	var oldValue = field.innerHTML
	
	field.innerHTML = newValue
	cr.expandField.expandFields[id] = oldValue
}
