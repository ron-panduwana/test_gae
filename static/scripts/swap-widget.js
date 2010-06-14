goog.provide('cr.swapWidget')

goog.require('goog.dom')

cr.swapWidget.swap = function(id) {
	var cField = goog.dom.$('swapWidget_' + id + '_c')
	var eField = goog.dom.$('swapWidget_' + id + '_e')
	
	if (cField.style.display == 'none') {
		cField.style.display = 'block'
		eField.style.display = 'none'
		
		// finding all INPUT nodes
		var inputNodes = goog.dom.findNodes(eField, function(node) {
			if (node.nodeType != Node.ELEMENT_NODE) return false
			return node.nodeName.toLowerCase() == 'input'
		})
		// finding all SELECT nodes
		var selectNodes = goog.dom.findNodes(eField, function(node) {
			if (node.nodeType != Node.ELEMENT_NODE) return false
			return node.nodeName.toLowerCase() == 'select'
		})
		
		// resetting all INPUT nodes values
		for (var i = 0 ; i < inputNodes.length ; ++i) {
			var node = inputNodes[i]
			node.value = node.getAttribute('value')
		}
		// resetting all SELECT nodes values
		for (var i = 0 ; i < selectNodes.length ; ++i) {
			var node = selectNodes[i]
			var idx = 0
			for (var j = 0 ; j < node.options.length ; ++j) {
				if (node.options[j].defaultSelected) {
					idx = j;
					break;
				}
			}
			node.selectedIndex = idx
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
