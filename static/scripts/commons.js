goog.provide('cr.commons');

String.format = function(text) {
	var args = arguments
	return text.replace(/\{(\d+)\}/g, function(capture, number) {
		return args[parseInt(number)+1]
	})
}

goog.exportSymbol('String.format', String.format);
