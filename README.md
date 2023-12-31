# SSLCertExpirySummary

The purpose of this project is to monitor SSL certificate expiry dates for sites.

### Project Functions:
- Card and list view
- Add/Edit/Remove SSL certificate's
- Filter based off Environment Type and/or Team
- Accounts (admin, regular)
- Add/Remove Users
- Add/Remove Environment Types
- Logging

### How to Setup your local environment:

1. Use VSCode (extensions: Python, Pylance)
   > to run without VSCode, see note in step 7 (you will still need to complete steps 2, 5, and 6)

2. Create a .env file in root of project with the following 2 lines:

     - `SECRET_KEY=<BAD_SECRET_KEY>`

     - `CONNECTION_STRING=postgresql://<dbuser>:<dbuser_password>@<servername>.<server_domain>:5432/<dbname>`

3. In VS Code, open the Command Palette (View > Command Palette or (Ctrl+Shift+P)). Then select the Python: Create Environment command to create a virtual environment in your workspace. Select venv and then the Python environment you want to use to create it.
4. After your virtual environment creation has been completed, run Terminal: Create New Terminal (Ctrl+Shift+`)) from the Command Palette, which creates a terminal and automatically activates the virtual environment by running its activation script.
   > Note: On Windows, if your default terminal type is PowerShell, you may see an error that it cannot run activate.ps1 because running scripts is disabled on the system. The error provides a link for information on how to allow scripts. Otherwise, use Terminal: Select Default Profile to set "Command Prompt" or "Git Bash" as your default instead.
5. Run the following commands in the terminal:

     - `pip install flask`

     - `pip install python-dotenv`

     - `pip install sqlalchemy`

     - `pip install pyOpenSSL`

     - `pip install psycopg2`
   
6. Create a db with the following tables
     #### certinfo
     | Column Name | Data Type | Allow Nulls |
     | ----------- | --------- | ----------- |
     | id | int | no |
     | name | nvarchar(150) | no |
     | address | nvarchar(150) | no |
     | port | int | no |
     | team | nvarchar(150) | no |
     | environmentid | int | no |

     > environmentid is a foreign key to id field in Environment table

     #### environment
     | Column Name | Data Type | Allow Nulls |
     | ----------- | --------- | ----------- |
     | id | int | no |
     | environment | nvarchar(100) | no |

     #### userinfo
     | Column Name | Data Type | Allow Nulls |
     | ----------- | --------- | ----------- |
     | id | int | no |
     | email | nvarchar(150) | no |
     | password | nvarchar(150) | no |
     | isadmin | int | no |
     > When you first register a user, you will need to update the isadmin field to 1. There is no way to make a user admin other than through the database.

7. In VSCode, map launch.json file to 'run and debug' configuration and click run
> Note: If running from command line, use the following 2 commands to run:

> `Set PYTHONHASHSEED=123`

> `flask --app app run --no-debugger --no-reload --host=0.0.0.0 --port 5000 &`

### Things I would improve on
- Dockerize the project
- Overall code base could use a cleanup/optimization
- Use object-relational mapping instead of raw sql
- Roll-over logging
- Setting the python hash seed in the launch.json file does not seem right


### Apache Compile and Configuration Changes ###

- Compile version of Apache 2.4.57
	cd ~
	mkdir dev
	cd dev
	tar -zxvf ~/httpd-2.4.57.tar.gz
	cd httpd-2.4.57
	./configure --enable-ssl=shared --enable-so --enable-http2 --with-ssl=/usr/local/lib64 --libdir=/usr/local/lib64
	make
	sudo make install
	# default installation directory is /usr/local/apache2
	sudo ldconfig
	
- Install Server certificate and its key 
	sudo cp ~/servername.cer /etc/ssl/certs/.
	sudo cp ~/servername.key /etc/ssl/certs/.

- Compile mod_ssl Apache module
  NOTE: python3 needed to be recompile with the following configure options:  --enable-optimizations --enable-shared --with-openssl-rpath=auto
	cd ~/dev
	tar -zxvf ~/mod_wsgi-5.0.0.tar.gz
	cd mod_wsgi-5.0.0
	./configure --with-apxs=/usr/local/apache2/bin/apxs --with-python=/usr/local/bin/python3
	make
	sudo make install

- clone latest revision of file local to base apache directory, ie: /usr/local/apache2
	git clone git@github.com:podsadd/SSLCertExpirySummary.git
	
- Change directory to clone project
	cd SSLCertExpirySummary
	
- Set required environment variables
	export PATH=/usr/local/pgsql/bin:$PATH
	export LD_LIBRARY_PATH=/usr/local/lib64:/usr/local/lib

- Create virtual env(ie: "webapp" as .py and .wsgi have references to webapp as the path) where flask will run, activate it and load dependent modules within the virtual env
	python3 -m venv webapp
	. webapp/bin/activate
	python3 -m pip install -r requirements.txt
	
- Replace/Update both apache configuration files with latest revisions of each
	cp ./apache2/conf/httpd.conf /usr/local/apache2/conf/httpd.conf
	cp ./apache2/conf/extra/rezmon.conf /usr/local/apache2/conf/extra/rezmon.conf
	
- Start Apache executable
  NOTE: Service could not be enabled for Oracle Linux 7.9 reasons while trying to compile mod_systemd.so
        All reboots of server will require that the Apache process be started by hand
	sudo /usr/local/apache2/bin/apachectl -k start

- After a few seconds, open a browser and load the servername root page, ie: https://servername/
