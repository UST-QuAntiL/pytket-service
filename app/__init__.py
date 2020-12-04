from flask import Flask
from app.config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from redis import Redis
import rq
from app import Config
import logging

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)

from app import routes, result_model, errors

app.redis = Redis.from_url(app.config['REDIS_URL'])
app.execute_queue = rq.Queue('pytket-service_execute', connection=app.redis, default_timeout=3600)
app.logger.setLevel(logging.INFO)
