#!/usr/local/bin/python3

import sys
sys.path.insert(0,'/usr/local/apache2/SSLCertExpirySummary')
sys.path.append('/usr/local/apache2/SSLCertExpirySummary/webapp/lib/python3.11/site-packages')

from app import app as application

