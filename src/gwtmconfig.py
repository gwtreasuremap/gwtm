import os

class Config(object):
    DEBUG = os.environ.get('DEBUG', 'False') == 'True'
    CSRF_ENABLED = True
    DB_USER = os.environ.get('DB_USER', 'treasuremap')
    DB_PWD = os.environ.get('DB_PWD', '')
    DB_NAME = os.environ.get('DB_NAME', 'treasuremap_dev')
    DB_HOST = os.environ.get('DB_HOST', 'db')
    DB_PORT = os.environ.get('DB_PORT', '5432')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_timeout': 300
    }
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'gwtreasuremap@gmail.com')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'gwtreasuremap@gmail.com')
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "")
    MAIL_PORT = os.environ.get("MAIL_PORT", 465)
    ADMINS = os.environ.get('ADMINS', 'gwtreasuremap@gmail.com')
    RECAPTCHA_PUBLIC_KEY = os.environ.get('RECAPTCHA_PUBLIC_KEY', '')
    RECAPTCHA_PRIVATE_KEY = os.environ.get('RECAPTCHA_PRIVATE_KEY', '')
    ZENODO_ACCESS_KEY = os.environ.get('ZENODO_ACCESS_KEY', '')
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', '')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
    AWS_DEFAULT_REGION = os.environ.get('AWS_DEFAULT_REGION', 'us-east-2')
    AWS_BUCKET = os.environ.get('AWS_BUCKET', 'gwtreasuremap')
    SECRET_KEY = os.urandom(16)
    CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://redis:6379')
    CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://redis:6379')
    CACHE_TYPE = 'RedisCache'
    CACHE_KEY_PREFIX = 'cache_'
    CACHE_REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379')
    CACHE_DEFAULT_TIMEOUT = 60 * 60 * 24
    AZURE_ACCOUNT_NAME = os.environ.get('AZURE_ACCOUNT_NAME', '')
    AZURE_ACCOUNT_KEY = os.environ.get('AZURE_ACCOUNT_KEY', '')
    STORAGE_BUCKET_SOURCE = os.environ.get('STORAGE_BUCKET_SOURCE', 's3')


    @property
    def SQLALCHEMY_DATABASE_URI(self):
        return f'postgresql://{self.DB_USER}:{self.DB_PWD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}'

config = Config()
