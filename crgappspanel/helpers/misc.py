class ValueWithRemoveLink(object):
    def __init__(self, value, remove_link=None):
        self.value = value
        self.remove_link = remove_link
    
    def __unicode__(self):
        return unicode(self.value)
