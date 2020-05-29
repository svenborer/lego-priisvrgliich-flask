from app import db

db.Model.metadata.reflect(db.engine)

class Set(db.Model):
    __table__ = db.Model.metadata.tables['tbl_sets']

    def __repr__(self):
        return '<Set {}|{}>'.format(self.set_number, self.name)

class ProviderScan(db.Model):
    __table__ = db.Model.metadata.tables['tbl_provider_scans']

    def __repr__(self):
        return '<ProviderScan {}>'.format(self.id)

class AuctionScan(db.Model):
    __table__ = db.Model.metadata.tables['tbl_auction_scans']

    def __repr__(self):
        return '<AuctionScan {}>'.format(self.id)

class BricklinkPrice(db.Model):
    __table__ = db.Model.metadata.tables['tbl_bricklink_prices']

    def __repr__(self):
        return '<BricklinkPrice {}>'.format(self.id)
