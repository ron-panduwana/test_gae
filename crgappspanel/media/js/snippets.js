goog.provide('cr.snippets');
goog.require('goog.async.Delay')
goog.require('goog.fx.dom.FadeOutAndHide')
goog.require('goog.structs.Map');
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


cr.snippets.userDialog = function(title, content, url) {
    var dialog= new goog.ui.Dialog()
    dialog.setTitle(title)
    dialog.setContent(content)
    var button_set = new goog.ui.Dialog.ButtonSet()
        .set(goog.ui.Dialog.DefaultButtonKeys.YES, gettext('Yes'), true)
        .set(goog.ui.Dialog.DefaultButtonKeys.NO, gettext('No'), false, true);
    dialog.setButtonSet(button_set)

    goog.events.listen(dialog, goog.ui.Dialog.EventType.SELECT, function(e) {
        if (e.key == 'yes') {
            open(url, '_self')
        }
    })
    return dialog;
}
goog.exportProperty(cr.snippets, 'userDialog', cr.snippets.userDialog);


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
        var button_set = new goog.ui.Dialog.ButtonSet()
            .set(goog.ui.Dialog.DefaultButtonKeys.YES, gettext('Yes'), true)
            .set(goog.ui.Dialog.DefaultButtonKeys.NO, gettext('No'), false, true);
        dialogDelete.setButtonSet(button_set)
        
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


var checked_cache = new goog.structs.Map();
cr.snippets.createRolePermissionChanged = function(checkbox) {
    if (checkbox.className != 'perm_read') {
        var checked = checkbox.checked;
        var tr = goog.dom.getAncestorByTagNameAndClass(checkbox, 'TR');
        var node = goog.dom.findNode(tr, function(node) {
            return node.className == 'perm_read';
        });
        var other_nodes = goog.dom.findNodes(tr, function(node) {
            return node.className == 'perm_add' ||
                node.className == 'perm_change';
        });
        var checked_len = 0;
        for (var i=0; i<other_nodes.length; i++) {
            if (other_nodes[i].checked) {
                checked_len++;
            }
        }
        if (node && checked && (checked_len == 1 || !node.disabled)) {
            checked_cache.set(node.getAttribute('name'), node.checked);
            node.checked = node.disabled = true;
        } else if (node && !checked && checked_len == 0) {
            node.disabled = false;
            var previous_val = checked_cache.get(node.getAttribute('name'));
            checked_cache.remove(node.getAttribute('name'));
            if (previous_val) {
                node.checked = previous_val;
            } else {
                node.checked = false;
            }
        }
    }
}
goog.exportProperty(cr.snippets, 'createRolePermissionChanged',
        cr.snippets.createRolePermissionChanged);


cr.snippets.createRoleInitPermissions = function() {
    var table = goog.dom.$$('table', 'roles');
    if (table.length) {
        table = table[table.length - 1];
        goog.dom.findNodes(table, function(node) {
            if (node.className == 'perm_add' || node.className == 'perm_change') {
                cr.snippets.createRolePermissionChanged(node);
            }
            return false;
        });
    }
}
goog.exportProperty(cr.snippets, 'createRoleInitPermissions',
        cr.snippets.createRoleInitPermissions);


goog.exportSymbol('cr.snippets', cr.snippets);
