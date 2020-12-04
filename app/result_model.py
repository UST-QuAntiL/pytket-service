from app import db


class Result(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    result = db.Column(db.String(1200), default="")
    complete = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return 'Result {}'.format(self.result)
