goog.provide('cr.snippets');
goog.require('goog.async.Delay')
goog.require('goog.fx.dom.FadeOutAndHide')
goog.require('cr.table');

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


cr.snippets.toggleSearch = function() {
    var f1 = goog.dom.$('shared-contact-search')
    var f2 = goog.dom.$('shared-contact-advanced-search')
    
    var vis = (f1.style.display == 'none')
    
    f1.style.display = vis ? 'block' : 'none'
    f2.style.display = vis ? 'none' : 'block'
}
goog.exportProperty(cr.snippets, 'toggleSearch', cr.snippets.toggleSearch);


cr.snippets.groupAutoComplete = function(suggestions) {
    new goog.ui.AutoComplete.Basic(suggestions, goog.dom.$('owner'), false)
    new goog.ui.AutoComplete.Basic(suggestions, goog.dom.$('member'), false)
}
goog.exportProperty(cr.snippets, 'groupAutoComplete', cr.snippets.groupAutoComplete);


cr.snippets.userSuspendDialog = function(title, content, url) {
    var dialogSuspend = new goog.ui.Dialog()
    dialogSuspend.setTitle(title)
    dialogSuspend.setContent(content)
    dialogSuspend.setButtonSet(goog.ui.Dialog.ButtonSet.YES_NO)

    goog.events.listen(dialogSuspend, goog.ui.Dialog.EventType.SELECT, function(e) {
        if (e.key == 'yes') {
            open(url, '_self')
        }
    })
    return dialogSuspend;
}
goog.exportProperty(cr.snippets, 'userSuspendDialog', cr.snippets.userSuspendDialog);


cr.snippets.userRestoreDialog = function(title, content, url) {
    var dialogRestore = new goog.ui.Dialog()
    dialogRestore.setTitle(title)
    dialogRestore.setContent(content)
    dialogRestore.setButtonSet(goog.ui.Dialog.ButtonSet.YES_NO)

    goog.events.listen(dialogRestore, goog.ui.Dialog.EventType.SELECT, function(e) {
        if (e.key == 'yes') {
            open(url, '_self')
        }
    })
}
goog.exportProperty(cr.snippets, 'userRestoreDialog', cr.snippets.userRestoreDialog);


cr.snippets.setUpListener = function() {
    goog.events.listen(window, 'unload', function() {
        goog.events.removeAll()
    })
}
goog.exportProperty(cr.snippets, 'setUpListener', cr.snippets.setUpListener);


cr.snippets.userShowDialog = function(dialog) {
    dialog.setVisible(true)
}
goog.exportProperty(cr.snippets, 'userShowDialog', cr.snippets.userShowDialog);


cr.snippets.removeSelectedHandler = function(title, content) {
    return function(list, removeUrl) {
        var dialogDelete = new goog.ui.Dialog()
        dialogDelete.setTitle(title)
        dialogDelete.setContent(content)
        dialogDelete.setButtonSet(goog.ui.Dialog.ButtonSet.YES_NO)
        
        goog.events.listenOnce(dialogDelete, goog.ui.Dialog.EventType.SELECT, function(e) {
            if (e.key == 'yes') {
                window.open(removeUrl, '_self')
            }
        })
        dialogDelete.setVisible(true)
    }
}
goog.exportProperty(cr.snippets, 'removeSelectedHandler', cr.snippets.removeSelectedHandler);


cr.snippets.savedWarning = function() {
    var hideSavedWarning = function() {
        var elem = goog.dom.$('saved-warning')
        var fadeOut = new goog.fx.dom.FadeOutAndHide(elem, 1000)
        fadeOut.play()
    }

    delay = new goog.async.Delay(hideSavedWarning, 5000);
    delay.start()
}
goog.exportProperty(cr.snippets, 'savedWarning', cr.snippets.savedWarning);


goog.exportSymbol('cr.snippets', cr.snippets);
