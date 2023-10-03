class SSLCert:
    def __init__(self, id, name, address, port, environment, environmentid, team, expiryDate = '', daysLeft = ''):
        self.id = id
        self.name = name
        self.address = address
        self.port = port
        self.environment = environment
        self.environmentid = environmentid
        self.team = team
        self.expiryDate = expiryDate
        self.daysLeft = daysLeft