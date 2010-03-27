goog.provide('cr.swapWidget')

goog.require('goog.dom')

cr.swapWidget.swap = function(id) {
	var cField = goog.dom.$('swapWidget_' + id + '_c')
	var eField = goog.dom.$('swapWidget_' + id + '_e')
	
	if (cField.style.display == 'none') {
		cField.style.display = 'block'
		eField.style.display = 'none'
	} else {
		cField.style.display = 'none'
		eField.style.display = 'block'
	}
}
