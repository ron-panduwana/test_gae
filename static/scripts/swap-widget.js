goog.provide('cr.swapWidget')

goog.require('goog.dom')

cr.swapWidget.swap = function(id) {
	var cField = goog.dom.$('swapWidget_' + id + '_c')
	var eField = goog.dom.$('swapWidget_' + id + '_e')
	
	if (cField.style.display == 'none') {
		cField.style.display = 'block'
		eField.style.display = 'none'
		
		var nodes = goog.dom.findNodes(eField, function(node) {
			if (node.nodeType != Node.ELEMENT_NODE) return false
			return node.nodeName.toLowerCase() == 'input'
		})
		
		for (var i = 0 ; i < nodes.length ; ++i) {
			var node = nodes[i]
			node.value = node.getAttribute('value')
		}
	} else {
		cField.style.display = 'none'
		eField.style.display = 'block'
		
		var nodes = goog.dom.findNodes(cField, function(node) {
			if (node.nodeType != Node.ELEMENT_NODE) return false
			return node.nodeName.toLowerCase() == 'input'
		})
		
		for (var i = 0 ; i < nodes.length ; ++i) {
			var node = nodes[i]
			node.value = node.getAttribute('value')
		}
	}
}
