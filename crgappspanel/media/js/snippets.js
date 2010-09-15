goog.provide('cr.snippets');
goog.require('goog.array');
goog.require('goog.async.Delay')
goog.require('goog.fx.dom.FadeOutAndHide')
goog.require('goog.structs.Map');
goog.require('goog.events');
goog.require('goog.ui.Checkbox');
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
    return function(list, removeUrl, buttons) {
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
            } else {
                for (var i=0; i < buttons.length; i++) {
                    buttons[i].disabled = false;
                }
            }
        })
        for (var i=0; i < buttons.length; i++) {
            buttons[i].disabled = true;
        }
        dialogDelete.setVisible(true);
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


var dependants_map = new goog.structs.Map();
var was_checked = new goog.structs.Map();
cr.snippets.permission = function(id, depends_on) {
    var permCheckbox = new goog.ui.Checkbox();
    permCheckbox.decorate(goog.dom.getElement(id));
    var input = permCheckbox.getContentElement();
    if (depends_on) {
        var dependants = dependants_map.get(depends_on);
        if (!dependants) {
            dependants = [input];
        } else {
            dependants.push(input);
        }
        dependants_map.set(depends_on, dependants);

        if (input.checked) {
            var depends_on_input = goog.dom.getElement(depends_on);
            if (depends_on_input) {
                depends_on_input.checked = true;
                depends_on_input.disabled = true;
            }
        }
    }

    var self_dependants = dependants_map.get(id);
    if (self_dependants) {
        var checked = goog.array.some(self_dependants, function(elem) {
            return elem.checked;
        });
        if (checked) {
            input.checked = input.disabled = true;
        }
    }
    was_checked.set(id, input.checked);

    goog.events.listen(permCheckbox, goog.ui.Component.EventType.CHANGE,
        function(e) {
            if (depends_on) {
                var checked = input.checked;
                var depends_on_input = goog.dom.getElement(depends_on);

                var dependants = dependants_map.get(depends_on);

                var others_checked = goog.array.some(
                    goog.array.filter(dependants, function(elem) {
                        return elem != input;
                    }),
                    function(elem) {
                        return elem.checked;
                    });

                if (checked && !others_checked) {
                    was_checked.set(depends_on, depends_on_input.checked);
                }

                var should_disable = goog.array.some(dependants, function(elem) {
                    return elem.checked;
                });

                var should_check = should_disable || was_checked.get(depends_on);

                depends_on_input.checked = should_check;
                depends_on_input.disabled = should_disable;
            }
        }
    );
}
goog.exportProperty(cr.snippets, 'permission', cr.snippets.permission);


cr.snippets.videoDialog = function(title, clip_id) {
    var dialog = new goog.ui.Dialog()
    dialog.setTitle(title)
    dialog.setContent(
            '<object width="800" height="600"><param name="allowfullscreen" value="true">' +
            '<param name="allowscriptaccess" value="always" />' +
            '<param name="movie" value="http://vimeo.com/moogaloop.swf?clip_id=' +
            clip_id + '&amp;server=vimeo.com&amp;show_title=0&amp;show_byline=0' +
            '&amp;show_portrait=0&amp;color=ff9933&amp;fullscreen=1&amp;autoplay=1' +
            '&amp;loop=0"/>' +
            '<embed src="http://vimeo.com/moogaloop.swf?clip_id=' +
            clip_id + '&amp;server=vimeo.com&amp;show_title=0&amp;show_byline=0' +
            '&amp;show_portrait=0&amp;color=ff9933&amp;fullscreen=1&amp;autoplay=1' +
            '&amp;loop=0" type="application/x-shockwave-flash" allowfullscreen="true" ' +
            'allowscriptaccess="always" width="800" height="600"></embed></object>');
    var button_set = new goog.ui.Dialog.ButtonSet()
        .set(goog.ui.Dialog.DefaultButtonKeys.OK, gettext('OK'), true);
    dialog.setButtonSet(button_set)

    goog.events.listen(dialog, goog.ui.Dialog.EventType.SELECT, function(e) {
        dialog.dispose();
    });
    dialog.setVisible(true);
    return false;
}
goog.exportProperty(cr.snippets, 'videoDialog', cr.snippets.videoDialog);


goog.exportSymbol('cr.snippets', cr.snippets);
