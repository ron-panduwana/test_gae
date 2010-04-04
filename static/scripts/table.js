goog.provide('cr.table')

goog.require('goog.dom')
goog.require('goog.net.XhrIo')

cr.table.tables = []
cr.table.deletes = []
cr.table.counts = []

cr.table.getTableName = function(name) {
	return name.substring(0, name.indexOf('_'))
}

cr.table.getNumber = function(name) {
	return name.substring(name.lastIndexOf('_')+1)
}

cr.table.getCheckbox = function(tableName, number) {
	if (number != null) {
		return goog.dom.$(String.format('{0}_select_{1}', tableName, number))
	} else {
		return goog.dom.$(String.format('{0}_select', tableName))
	}
}

cr.table.getTableRow = function(tableName, number) {
	if (number != null) {
		return goog.dom.$(String.format('{0}_row_{1}', tableName, number))
	} else {
		return goog.dom.$(String.format('{0}_row', tableName))
	}
}

cr.table.getDeleteButton = function(tableName, number) {
	return goog.dom.$(String.format('{0}_delete_{1}', tableName, number))
}

cr.table.getElementCount = function(tableName) {
	if (!cr.table.counts[tableName]) {
		var i = 0
		while (cr.table.getTableRow(tableName, i)) ++i
		cr.table.counts[tableName] = i
	}
	return cr.table.counts[tableName]
}

cr.table.showDetails = function(obj) {
	window.open(String.format('{0}/details/', obj), '_self')
}

cr.table.onSelectAll = function(obj) {
	var tableName = cr.table.getTableName(obj.id)
	var count = cr.table.getElementCount(tableName)
	
	for (var i = 0 ; i < count ; ++i) {
		cr.table.getCheckbox(tableName, i).checked = obj.checked
		cr.table.getTableRow(tableName, i).className = (obj.checked) ? 'selected' : ''
	}
	
	cr.table.getDeleteButton(tableName, 1).disabled = !obj.checked
	cr.table.getDeleteButton(tableName, 2).disabled = !obj.checked
}

cr.table.onSelectRow = function(obj) {
	var tableName = cr.table.getTableName(obj.id)
	var count = cr.table.getElementCount(tableName)
	
	cr.table.getTableRow(tableName, cr.table.getNumber(obj.id)).className = (obj.checked) ? 'selected' : ''
	
	var selCount = 0
	for (var i = 0 ; i < count ; ++i) {
		if (cr.table.getCheckbox(tableName, i).checked) ++selCount
	}
	
	cr.table.getCheckbox(tableName, null).checked = (selCount == count)
	cr.table.getDeleteButton(tableName, 1).disabled = (selCount == 0)
	cr.table.getDeleteButton(tableName, 2).disabled = (selCount == 0)
}

cr.table.onDeleteClicked = function(obj) {
	var tableName = cr.table.getTableName(obj.id)
	var count = cr.table.getElementCount(tableName)
	
	var list = []
	for (var i = 0 ; i < count ; ++i) {
		if (cr.table.getCheckbox(tableName, i).checked) {
			list.push(cr.table.tables[tableName][i])
		}
	}
	
	cr.table.deletes[tableName](list, function() {
		for (var i = 0 ; i < list.length ; ++i) {
			var uri = String.format('{0}/remove/', list[i])
			goog.net.XhrIo.send(uri)
		}
	})
}