goog.require('goog.dom')

counts = {}

function _getTableName(name) {
	return name.substring(0, name.indexOf('_'))
}

function _getNumber(name) {
	return name.substring(name.lastIndexOf('_')+1)
}

function _getCheckboxName(tableName, number) {
	if (number != null) {
		return String.format('{0}_select_{1}', tableName, number)
	} else {
		return String.format('{0}_select', tableName)
	}
}

function _getTableRowName(tableName, number) {
	if (number != null) {
		return String.format('{0}_row_{1}', tableName, number)
	} else {
		return String.format('{0}_row', tableName)
	}
}

function _getElementCount(tableName) {
	if (!counts[tableName]) {
		var i = 0
		while (goog.dom.$(_getTableRowName(tableName, i))) ++i
		counts[tableName] = i
	}
	return counts[tableName]
}

function showDetails(obj) {
	open(obj + '/', '_self')
}

function onSelectAll(obj) {
	var tableName = _getTableName(obj.id)
	var count = _getElementCount(tableName)
	
	for (var i = 0 ; i < count ; ++i) {
		goog.dom.$(_getCheckboxName(tableName, i)).checked = obj.checked
		goog.dom.$(_getTableRowName(tableName, i)).className = (obj.checked) ? 'selected' : ''
	}
}

function onSelectRow(obj) {
	var tableName = _getTableName(obj.id)
	var count = _getElementCount(tableName)
	
	goog.dom.$(_getTableRowName(tableName, _getNumber(obj.id))).className = (obj.checked) ? 'selected' : ''
	
	var selCount = 0
	for (var i = 0 ; i < count ; ++i) {
		if (goog.dom.$(_getCheckboxName(tableName, i)).checked) ++selCount
	}
	
	goog.dom.$(_getCheckboxName(tableName, null)).checked = (selCount == count)
}
