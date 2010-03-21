goog.require('goog.dom')

counts = {}

function _baseName(name) {
	return name.substring(0, name.lastIndexOf('_'))
}

function _childName(name, index) {
	return name + '_' + index
}

function _getElementCount(name) {
	if (!counts[name]) {
		var i = 0
		while (goog.dom.$(_childName(name, i))) ++i
		counts[name] = i
	}
	return counts[name]
}

function showDetails(obj) {
	open(obj + '/', '_self')
}

function onSelectAll(obj) {
	var count = _getElementCount(obj.id)
	
	for (var i = 0 ; i < count ; ++i) {
		goog.dom.$(_childName(obj.id, i)).checked = obj.checked
	}
}

function onSelectRow(obj) {
	var base = _baseName(obj.id)
	var count = _getElementCount(base)
	
	var selCount = 0
	for (var i = 0 ; i < count ; ++i) {
		if (goog.dom.$(_childName(base, i)).checked) ++selCount
	}
	
	goog.dom.$(base).checked = (selCount == count)
}
