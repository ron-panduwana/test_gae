goog.provide('cr.table')

goog.require('goog.dom')

cr.table.counts = {}

cr.table.getTableName = function(name) {
	return name.substring(0, name.indexOf('_'))
}

cr.table.getNumber = function(name) {
	return name.substring(name.lastIndexOf('_')+1)
}

cr.table.getCheckboxName = function(tableName, number) {
	if (number != null) {
		return String.format('{0}_select_{1}', tableName, number)
	} else {
		return String.format('{0}_select', tableName)
	}
}

cr.table.getTableRowName = function(tableName, number) {
	if (number != null) {
		return String.format('{0}_row_{1}', tableName, number)
	} else {
		return String.format('{0}_row', tableName)
	}
}

cr.table.getElementCount = function(tableName) {
	if (!cr.table.counts[tableName]) {
		var i = 0
		while (goog.dom.$(cr.table.getTableRowName(tableName, i))) ++i
		cr.table.counts[tableName] = i
	}
	return cr.table.counts[tableName]
}

cr.table.showDetails = function(obj) {
	open(obj + '/', '_self')
}

cr.table.onSelectAll = function(obj) {
	var tableName = cr.table.getTableName(obj.id)
	var count = cr.table.getElementCount(tableName)
	
	for (var i = 0 ; i < count ; ++i) {
		goog.dom.$(cr.table.getCheckboxName(tableName, i)).checked = obj.checked
		goog.dom.$(cr.table.getTableRowName(tableName, i)).className = (obj.checked) ? 'selected' : ''
	}
}

cr.table.onSelectRow = function(obj) {
	var tableName = cr.table.getTableName(obj.id)
	var count = cr.table.getElementCount(tableName)
	
	goog.dom.$(cr.table.getTableRowName(tableName, cr.table.getNumber(obj.id))).className = (obj.checked) ? 'selected' : ''
	
	var selCount = 0
	for (var i = 0 ; i < count ; ++i) {
		if (goog.dom.$(cr.table.getCheckboxName(tableName, i)).checked) ++selCount
	}
	
	goog.dom.$(cr.table.getCheckboxName(tableName, null)).checked = (selCount == count)
}
