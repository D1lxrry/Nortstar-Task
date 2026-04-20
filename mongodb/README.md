# NorthStar MongoDB Atlas setup

This folder contains everything needed to connect your Mac to the MongoDB Atlas
cluster called NorthStar, which is the free tier cluster you will use for the
Databases and Analytics coursework.

## Files in this folder

- `.env` is where your secret connection string lives. Never share or commit this file.
- `test_connection.py` pings the cluster and lists the databases to confirm the setup works.
- `.gitignore` keeps `.env` out of git if you later version control this folder.
- `README.md` is this file.

## 3 step setup

### Step 1: install the 1 missing Python package

PyMongo is already installed. You still need python-dotenv so the script can
read your secret connection string from the `.env` file. In Terminal run:

```
python3 -m pip install python-dotenv
```

### Step 2: paste your Atlas connection string into .env

1. Open `.env` in a text editor (TextEdit, VS Code, or any editor).
2. Find the line that reads `MONGODB_URI=""`.
3. Paste the full SRV string from Atlas between the quotes. It looks like:

```
mongodb+srv://larryco211_db_user:YOUR_PASSWORD@northstar.xxxxxx.mongodb.net/?appName=NorthStar
```

4. Save the file. Close it.

If you accidentally lost the connection string, you can find it again in Atlas
under Database, then Connect, then Drivers, but Atlas will only show the
password again if you reset it under Database Access.

### Step 3: run the test

In Terminal:

```
cd "~/Documents/University Work/Databases&Analytics/Databases and Anallytics Assesment/mongodb"
python3 test_connection.py
```

A successful run prints:

```
Connecting to MongoDB Atlas...
Connection OK. Ping successful.

Databases on this cluster:
  - admin
  - local
  - sample_airbnb
  - sample_analytics
  - sample_geospatial
  - sample_mflix
  - sample_restaurants
  - sample_supplies
  - sample_training
  - sample_weatherdata
```

And also shows 1 example document from the Airbnb dataset.

## Common errors and fixes

- **MONGODB_URI is empty:** you forgot to paste the connection string into `.env`.
- **Authentication failed:** wrong password. Reset it in Atlas under Database Access.
- **Could not reach the cluster:** you are offline, or your current IP is not on the
  Atlas Network Access list. Sign in to Atlas, go to Network Access, and add
  your current IP.
- **dnspython not found:** rerun `python3 -m pip install "pymongo[srv]"`.

## Once this works

You are ready to start the actual coursework tasks. Typical next steps are:

1. Load the NorthStar CSV or JSON data into MongoDB using `pymongo.insert_many`.
2. Write queries in Python to answer the assignment questions.
3. Pull query results into pandas or into R for analysis and charts.

Ask Claude for help any time, and always work from this folder so the `.env`
file is picked up automatically.
