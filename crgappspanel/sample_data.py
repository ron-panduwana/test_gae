class SampleUser(object):
    def __init__(self, title=None, user_name=None, given_name=None, family_name=None,
            password=None, suspended=None, admin=None, quota=None, roles=None, last_login=None):
        self.title = title
        self.user_name = user_name
        self.given_name = given_name
        self.family_name = family_name
        self.password = password
        self.suspended = suspended
        self.admin = admin
        self.quota = quota
        self.roles = roles
        self.last_login = last_login
    
    def get_full_name(self):
        return '%s %s' % (self.given_name, self.family_name)

class SampleGroup(object):
    def __init__(self, title=None, name=None, kind=None):
        self.title = title
        self.name = name
        self.kind = kind

def get_sample_users():
    return [
        SampleUser(
            given_name='Pawel',
            family_name='Zaborski',
            user_name='pawel',
            admin='True',
            quota='0% of 25 GB',
            roles='admin',
            last_login='10:28 pm'),
        SampleUser(
            given_name='Roland',
            family_name='Plaszowski',
            user_name='roland',
            admin='True',
            quota='0% of 25 GB',
            roles='admin',
            last_login='Jan 6'),
        SampleUser(
            given_name='Kamil',
            family_name='Klimkiewicz',
            user_name='kamil',
            admin='True',
            quota='0% of 25 GB',
            roles='admin',
            last_login='3:15 pm'),
        SampleUser(
            given_name='sky',
            family_name='mail',
            user_name='skymail',
            admin='False',
            quota='3% of 25 GB',
            roles='sample',
            last_login='Mar 15'),
    ]

def get_sample_groups():
    return [
        SampleGroup(
            title='Agent Portugal',
            name='agent.pt',
            kind='Custom'),
        SampleGroup(
            title='All Polish speakers',
            name='all.polish.speakers',
            kind='Custom'),
    ]
