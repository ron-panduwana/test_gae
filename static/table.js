goog.require('goog.dom')

counts = {}

function baseName(name) {
	return name.substring(0, name.lastIndexOf('_'))
}

function childName(name, index) {
	return name + '_' + index
}

function getElementCount(name) {
	if (!counts[name]) {
		var i = 0
		while (goog.dom.$(childName(name, i))) ++i
		counts[name] = i
	}
	return counts[name]
}

function onSelectAll(obj) {
	var count = getElementCount(obj.id)
	
	for (var i = 0 ; i < count ; ++i) {
		goog.dom.$(childName(obj.id, i)).checked = obj.checked
	}
}

function onSelectRow(obj) {
	var base = baseName(obj.id)
	var count = getElementCount(base)
	
	var selCount = 0
	for (var i = 0 ; i < count ; ++i) {
		if (goog.dom.$(childName(base, i)).checked) ++selCount
	}
	
	goog.dom.$(base).checked = (selCount == count)
}
