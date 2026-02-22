import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from time import sleep
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime

# Try to import BeautifulSoup; if not installed, install it at runtime and import again.
try:
	from bs4 import BeautifulSoup
except ImportError:
	import sys
	import subprocess
	subprocess.check_call([sys.executable, "-m", "pip", "install", "beautifulsoup4"])
	from bs4 import BeautifulSoup

import logging