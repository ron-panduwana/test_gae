goog.provide('cr.table')

goog.require('goog.dom')
goog.require('goog.net.XhrIo')
goog.require('goog.ui.Dialog')

cr.table.tables = []
goog.exportProperty(cr.table, 'tables', cr.table.tables);
cr.table.deletes = []
goog.exportProperty(cr.table, 'deletes', cr.table.deletes);
cr.table.counts = []
goog.exportProperty(cr.table, 'counts', cr.table.counts);

cr.table.getTableName = function(name) {
	return name.substring(0, name.indexOf('_'))
}
goog.exportProperty(cr.table, 'getTableName', cr.table.getTableName);

cr.table.getNumber = function(name) {
	return name.substring(name.lastIndexOf('_')+1)
}
goog.exportProperty(cr.table, 'getNumber', cr.table.getNumber);

cr.table.getCheckbox = function(tableName, number) {
	if (number != null) {
		return goog.dom.$(String.format('{0}_select_{1}', tableName, number))
	} else {
		return goog.dom.$(String.format('{0}_select', tableName))
	}
}
goog.exportProperty(cr.table, 'getCheckbox', cr.table.getCheckbox);

cr.table.getTableRow = function(tableName, number) {
	if (number != null) {
		return goog.dom.$(String.format('{0}_row_{1}', tableName, number))
	} else {
		return goog.dom.$(String.format('{0}_row', tableName))
	}
}
goog.exportProperty(cr.table, 'getTableRow', cr.table.getTableRow);

cr.table.getDeleteButton = function(tableName, number) {
	return goog.dom.$(String.format('{0}_delete_{1}', tableName, number))
}
goog.exportProperty(cr.table, 'getDeleteButton', cr.table.getDeleteButton);

cr.table.getElementCount = function(tableName) {
	if (!cr.table.counts[tableName]) {
		var i = 0
		while (cr.table.getTableRow(tableName, i)) ++i
		cr.table.counts[tableName] = i
	}
	return cr.table.counts[tableName]
}
goog.exportProperty(cr.table, 'getElementCount', cr.table.getElementCount);

cr.table.showDetails = function(obj) {
	window.open(String.format('../details/{0}/', obj), '_self');
    return false;
}
goog.exportProperty(cr.table, 'showDetails', cr.table.showDetails);

cr.table.onSelectAll = function(obj) {
	var tableName = cr.table.getTableName(obj.id);
	var count = cr.table.getElementCount(tableName);
	
    var checkbox_len = 0;
	for (var i = 0 ; i < count ; ++i) {
        var checkbox = cr.table.getCheckbox(tableName, i);
        if (checkbox) {
            checkbox.checked = obj.checked;
            checkbox_len++;
        }
		cr.table.getTableRow(tableName, i).className = (obj.checked) ? 'data selected' : 'data'
	}
	
	cr.table.getDeleteButton(tableName, 1).disabled = !obj.checked || !checkbox_len;
	cr.table.getDeleteButton(tableName, 2).disabled = !obj.checked || !checkbox_len;
}
goog.exportProperty(cr.table, 'onSelectAll', cr.table.onSelectAll);

cr.table.onSelectRow = function(obj) {
	var tableName = cr.table.getTableName(obj.id)
	var count = cr.table.getElementCount(tableName)
	
	cr.table.getTableRow(tableName, cr.table.getNumber(obj.id)).className = (obj.checked) ? 'data selected' : 'data'
	
	var selCount = 0
	for (var i = 0 ; i < count ; ++i) {
        var checkbox = cr.table.getCheckbox(tableName, i);
        if (checkbox && checkbox.checked) {
            ++selCount;
        }
	}
	
	cr.table.getCheckbox(tableName, null).checked = (selCount == count)
	cr.table.getDeleteButton(tableName, 1).disabled = (selCount == 0)
	cr.table.getDeleteButton(tableName, 2).disabled = (selCount == 0)
}
goog.exportProperty(cr.table, 'onSelectRow', cr.table.onSelectRow);

cr.table.onDeleteClicked = function(obj) {
	var tableName = cr.table.getTableName(obj.id)
	var count = cr.table.getElementCount(tableName)
	
	var list = ''
	for (var i = 0 ; i < count ; ++i) {
        var checkbox = cr.table.getCheckbox(tableName, i);
		if (checkbox && checkbox.checked) {
			if (list != '') list += '/'
			list += cr.table.tables[tableName][i]
		}
	}
	
    var buttons = [
        goog.dom.$(tableName + '_delete_1'), goog.dom.$(tableName + '_delete_2')];
	cr.table.deletes[tableName](list, String.format('../remove/{0}/', list), buttons)
}
goog.exportProperty(cr.table, 'onDeleteClicked', cr.table.onDeleteClicked);

goog.exportSymbol('cr.table', cr.table);
