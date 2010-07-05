goog.provide('cr.feedback');
goog.require('goog.net.XhrIo');
goog.require('goog.ui.Dialog');
goog.require('goog.structs.Map');
goog.require('goog.Uri.QueryData');

var ACTION = 'https://www.salesforce.com/servlet/servlet.WebToCase?encoding=UTF-8';
var ORG_ID = '00D20000000KMfv';

function feedback(type) {
    var feedbackDialog = new goog.ui.Dialog();
    if (type == 'Feedback') {
        feedbackDialog.setTitle('Feedback');
    } else {
        feedbackDialog.setTitle('Report a problem');
    }
    feedbackDialog.setContent(
            '<form id="feedback" method="POST" action="' + ACTION + '">' +
            '<input type="hidden" name="orgid" value="' + ORG_ID + '"/>' +
            '<input type="hidden" name="retURL" value="' + feedback_url + '"/>' +
            '<input type="hidden" name="type" value="' + type + '"/>' +
            '<input type="hidden" name="email" value="' + email + '"/>' +
            '<input type="hidden" name="external" value="1"/>' +
            '<table><tr><th>' +
            '<label for="subject">Subject:</label> ' +
            '</th><td>' +
            '<input id="subject" maxlength="80" name="subject" size="20"/>' +
            '</td></tr><tr><th>' +
            '<label for="description">Description:</label> ' +
            '</th><td>' +
            '<textarea rows="10" cols="50" name="description" ' +
            'id="description"></textarea>' +
            '</td></tr></table>' +
            '</form>'
            );
    feedbackDialog.setButtonSet(goog.ui.Dialog.ButtonSet.OK_CANCEL);
    feedbackDialog.setVisible(true);
    document.getElementById('subject').focus();
    goog.events.listen(feedbackDialog, goog.ui.Dialog.EventType.SELECT, function(e) {
        if (e.key == 'ok') {
            var subject = document.getElementById('subject').value;
            var description = document.getElementById('description').value;

            if (subject && description) {
                document.getElementById('description').value = 'URL: ' + window.location + '\n' + description;
                document.getElementById('feedback').submit();
            } else {
                alert('Please enter both subject and description.');
                return false;
            }
        }
        feedbackDialog.dispose();
    });
    return false;
}
goog.exportSymbol('feedback', feedback);


function buyNow() {
    var dialog = new goog.ui.Dialog();
    dialog.setTitle('Buy now');
    dialog.setContent(
            '<form id="feedback" method="POST" action="' + ACTION + '">' +
            '<input type="hidden" name="orgid" value="' + ORG_ID + '"/>' +
            '<input type="hidden" name="retURL" value="' + feedback_url + '"/>' +
            '<input type="hidden" name="external" value="1"/>' +
            '<table><tr><th>' +
            '<label for="name">Name:</label> ' +
            '</th><td>' +
            '<input id="name" maxlength="80" name="name" size="20"/>' +
            '</td></tr><tr><th>' +
            '<label for="company">Company:</label> ' +
            '</th><td>' +
            '<input id="company" maxlength="80" name="company" size="20"/>' +
            '</td></tr><tr><th>' +
            '<label for="company">Phone:</label> ' +
            '</th><td>' +
            '<input id="phone" maxlength="80" name="phone" size="20"/>' +
            '</td></tr><tr><th>' +
            '<label for="email">Email address:</label> ' +
            '</th><td>' +
            '<input id="email" maxlength="80" name="email" size="20" value="' + email + '"/>' +
            '</td></tr><tr><th>' +
            '<label for="address">Address:</label> ' +
            '</th><td>' +
            '<textarea rows="4" cols="30" name="address" ' +
            'id="address"></textarea>' +
            '</td></tr></table>' +
            '</form>'
            );
    dialog.setButtonSet(goog.ui.Dialog.ButtonSet.OK_CANCEL);
    dialog.setVisible(true);
    goog.events.listen(dialog, goog.ui.Dialog.EventType.SELECT, function(e) {
        dialog.dispose();
    });
    return false;
}
goog.exportSymbol('buyNow', buyNow);
