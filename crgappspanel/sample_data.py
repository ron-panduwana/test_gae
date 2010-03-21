def get_sample_users():
    return [
        {
            'given_name': 'Pawel',
            'family_name': 'Zaborski',
            'user_name': 'pawel@moroccanholidayrental.com',
            'admin': 'True',
            'quota': '0% of 25 GB',
            'roles': 'admin',
            'last_login': '9:28 pm',
        },
        {
            'given_name': 'Roland',
            'family_name': 'Plaszowski',
            'user_name': 'roland@moroccanholidayrental.com',
            'admin': 'True',
            'quota': '0% of 25 GB',
            'roles': 'admin',
            'last_login': 'Jan 6',
        },
        {
            'given_name': 'Kamil',
            'family_name': 'Klimkiewicz',
            'user_name': 'kamil@moroccanholidayrental.com',
            'admin': 'True',
            'quota': '0% of 25 GB',
            'roles': 'admin',
            'last_login': '3:15 pm',
        },
        {
            'given_name': 'sky',
            'family_name': 'mail',
            'user_name': 'skymail@moroccanholidayrental.com',
            'admin': 'False',
            'quota': '3% of 25 GB',
            'roles': 'sample',
            'last_login': 'Mar 15',
        },
    ]

def get_sample_groups():
    return [
        {
            'name': 'Agent Portugal',
            'email': 'agent.pt@moroccanholidayrental.com',
            'type': 'Custom',
        },
        {
            'name': 'All Polish speakers',
            'email': 'all.polish.speakers@moroccanholidayrental.com',
            'type': 'Custom',
        },
    ]
