import pymongo
from pymongo import MongoClient

client = MongoClient('localhost', 27017)

# Get the sampleDB database
db = client.Crypto


