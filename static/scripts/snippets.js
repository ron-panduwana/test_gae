goog.provide('cr.snippets');

cr.snippets.vacationStateChanged = function(value) {
    if (!value) {
        value = goog.dom.$('id_state').value;
    }
    if (value == 'true') {
        goog.dom.$('id_subject').removeAttribute('disabled');
        goog.dom.$('id_message').removeAttribute('disabled');
        goog.dom.$('id_contacts_only').removeAttribute('disabled');
    } else {
        goog.dom.$('id_subject').setAttribute('disabled', 'disabled');
        goog.dom.$('id_message').setAttribute('disabled', 'disabled');
        goog.dom.$('id_contacts_only').setAttribute('disabled', 'disabled');
    }
}
goog.exportProperty(cr.snippets, 'vacationStateChanged', cr.snippets.vacationStateChanged);

goog.exportSymbol('cr.snippets', cr.snippets);
