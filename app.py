from flask import Flask, redirect, render_template, request, session, url_for
from sqlalchemy import create_engine, text
from dotenv import dotenv_values
import OpenSSL, ssl, datetime, json, logging, models.EnvironmentModel, models.SSLCertModel

config = dotenv_values(".env")
logging.basicConfig(filename='flaskAppLog.log', level=logging.INFO)

app = Flask(__name__, template_folder='templateFiles')
app.secret_key = config['SECRET_KEY'] 

engine = create_engine(config['CONNECTION_STRING'])

def loadCerts(environmentid=-1, team='%'):
    certList = []
    query = ''
    if (int(environmentid) != -1):
        query = "SELECT CertInfo.id, name, address, port, team, environment, environmentid FROM CertInfo JOIN Environment ON certInfo.environmentid = Environment.id WHERE certInfo.environmentid = " + environmentid + " AND certInfo.team LIKE '" + team + "';"
    else:
        query = "SELECT CertInfo.id, name, address, port, team, environment, environmentid FROM CertInfo JOIN Environment ON certInfo.environmentid = Environment.id WHERE certInfo.team LIKE '" + team + "';"

    results=[]
    try:
        results = engine.connect().execute(text(query))
    except:
        engine.dispose()
        app.logger.warning("There was an issue running the loadCerts() query.")
        return -1

    for row in results:
        jsonResult = row._mapping
        errorCert = False
        
        try:
            cert = ssl.get_server_certificate((jsonResult.address, jsonResult.port))
        except:
            errorCert = True

        if (not errorCert):
            x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert)
            time = datetime.datetime.strptime(x509.get_notAfter().decode('utf-8'), '%Y%m%d%H%M%S%z').date()
            expiryDate = time.isoformat()
            daysLeft = (datetime.datetime(time.year, time.month, time.day) - datetime.datetime.now()).days

            certList.append(models.SSLCertModel.SSLCert(jsonResult.id, jsonResult.name, jsonResult.address, jsonResult.port, jsonResult.environment, jsonResult.environmentid, jsonResult.team, expiryDate, daysLeft))
        else:
            certList.append(models.SSLCertModel.SSLCert(jsonResult.id, "***ERROR CERT*** " + jsonResult.name, jsonResult.address, jsonResult.port, jsonResult.environment, jsonResult.environmentid, jsonResult.team, expiryDate, daysLeft))
 
    certList.sort(key=lambda x: x.daysLeft)
    return json.loads(json.dumps([obj.__dict__ for obj in certList]))

def getEnvironmentTypes():
    environmentList = []
    results = []
    query = 'SELECT * FROM Environment;'
    try:
        results = engine.connect().execute(text(query))
    except:
        engine.dispose()
        app.logger.warning("There was an issue running the getEnvironmentTypes() query.")
        return -1

    for row in results:
        jsonResult = row._mapping
        environmentList.append(models.EnvironmentModel.Environment(jsonResult.id, jsonResult.environment))

    return json.loads(json.dumps([obj.__dict__ for obj in environmentList]))

def getTeamList():
    teamList = []
    results = []
    query = "SELECT DISTINCT team from CertInfo;"
    try:
        results = engine.connect().execute(text(query))
    except:
        engine.dispose()
        app.logger.warning("There was an issue running the getTeamList() query.")
        return -1

    for row in results:
        jsonResult = row._mapping
        teamList.append(jsonResult)

    return teamList

def validateCert(address, port):
    try:
        ssl.get_server_certificate((address, port))
        app.logger.info("cert with address=" + address +" was valid")
        return True
    except:
        app.logger.warning("cert with address=" + address +" was invalid")
        return False

def testDBConnection():
    try:
        create_engine(config['CONNECTION_STRING']).connect()
    except:
        return False
    return True

@app.route('/', methods=['GET','POST'])
def index():
    environmentid = -1
    team = '%'
    if request.method == 'POST':
        environmentid = request.form['environmentSelect']
        team = request.form['teamSelect']
        if environmentid == 'Choose Environment':
            environmentid = '-1'
        if team == 'Choose Team':
            team = '%'

    app.logger.info("/ page called with environmentid=" + str(environmentid) + ", team=" + team + ", ip=" + request.remote_addr)
    return render_template('index.html', jsonList=loadCerts(environmentid, team), environmentList=getEnvironmentTypes(), teamList=getTeamList(), errors={})

@app.route('/list', methods=['GET','POST'])
def list():
    environmentid = -1
    team = '%'
    if request.method == 'POST':
        environmentid = request.form['environmentSelect']
        team = request.form['teamSelect']
        if environmentid == 'Choose Environment':
            environmentid = '-1'
        if team == 'Choose Team':
            team = '%'
    app.logger.info("/list page called with environmentid=" + str(environmentid) + ", team=" + team + ", ip=" + request.remote_addr)
    return render_template('list.html', jsonList=loadCerts(environmentid, team), environmentList=getEnvironmentTypes(), teamList=getTeamList(), errors={})

@app.route('/login', methods=['GET', 'POST'])
def login():
    errors={}
    if request.method == 'POST':
        email = request.form['inputEmail']
        password = str(hash(request.form['inputPassword']))

        results=[]
        query = "SELECT * FROM UserInfo WHERE email='" + email + "' AND password='" + password + "';"
        try:
            results = engine.connect().execute(text(query))
        except:
            engine.dispose()
            app.logger.warning("There was a problem executing the login query.")
            errors['queryError'] = ['There was a problem executing the query.']
            return render_template('login.html', errors=errors)

        for row in results:
            if row._mapping.isadmin == 1:
                    session['isadmin'] = 1
            session['email'] = email
            app.logger.info("/login with email=" + email + " and ip =" + request.remote_addr)
            return redirect(url_for('index'))

        errors['loginError'] = ['That email and password combination is invalid.']
        return render_template('login.html', errors=errors)

    return render_template('login.html', errors={})

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    errors={}
    if request.method == 'POST':
        email = request.form['inputEmail']
        password = str(hash(request.form['inputPassword']))

        results=[]
        query = "SELECT * FROM UserInfo WHERE email='" + email + "';"
        try:
            results = engine.connect().execute(text(query))
        except:
            engine.dispose()
            app.logger.warning("There was a problem executing the query getting email information.")
            errors['queryError'] = ['There was a problem executing the query.']
            return render_template('signup.html', errors=errors)

        if len(results.all()) == 0:
            query = "INSERT INTO UserInfo(email, password, isadmin) VALUES ('" + email + "', '" + password + "', 0 );"
            try:
                conn = engine.connect()
                results = conn.execute(text(query))
                conn.commit()
            except:
                engine.dispose()
                app.logger.warning("There was a problem executing the insert query for signup.")
                errors['queryError'] = ['There was a problem executing the query.']
                return render_template('signup.html', errors=errors)
            
            session['email'] = email
            app.logger.info("/signup with email=" + email + " and ip =" + request.remote_addr)
            return redirect(url_for('index'))
        else:
            errors['signupError'] = ['That email is already in use by another account.']
            return render_template('signup.html', errors=errors)

    return render_template('signup.html', errors=errors)

@app.route('/logout')
def logout():
    if len(session) == 0:
        return redirect(url_for('index'))
    
    app.logger.info("/logout page has been called by user=" + session['email'] +" from ip=" + request.remote_addr)
    session.clear()
    return redirect(url_for('index'))

@app.route('/add', methods=['GET', 'POST'])
def add():
    if session.get('email') == None:
        return redirect(url_for('index'))
    
    errors={}
    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        port = request.form['port']
        team = request.form['team']
        environmentid = request.form['environmentSelect']

        if environmentid == 'Choose Environment':
            errors['environmentSelectError'] = ['You did not select an environment.']
            return render_template("addcert.html", environmentList=getEnvironmentTypes(), errors=errors)

        if not validateCert(address, int(port)):
            errors['invalidCertError'] = ['The address and port you provided does not give a valid SSL certificate.']
            return render_template("addcert.html", environmentList=getEnvironmentTypes(), errors=errors)

        query = "INSERT INTO CertInfo(name, address, port, team, environmentid) VALUES ('" + name + "', '" + address + "', '" + port + "', '" + team + "', " + str(environmentid) + ");"
        try:
            conn = engine.connect()
            conn.execute(text(query))
            conn.commit()
        except:
            engine.dispose()
            app.logger.warning("There was a problem executing the add certificate query.")
            errors['queryError'] = ['There was a problem executing the add certificate query.']
            return render_template("addcert.html", environmentList=getEnvironmentTypes(), errors=errors)

        app.logger.info("/add page was called with name=" + name + ", address=" + address + ", port=" + port + ", team=" + team + ", environmentid=" + str(environmentid) + ", and ip =" + request.remote_addr)
        return redirect(url_for('index'))
    
    return render_template("addcert.html", environmentList=getEnvironmentTypes(), errors=errors)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    if session.get('email') == None:
        return redirect(url_for('index'))
    
    errors={}
    cert = ''
    results = []
    query = 'SELECT CertInfo.id, name, address, port, team, environment, environmentid FROM CertInfo JOIN Environment ON certInfo.environmentid = Environment.Id;'
    try:
        results = engine.connect().execute(text(query))
    except:
        engine.dispose()
        app.logger.warning("There was a problem executing the query to get the certicate information on /edit/<id>.")
        errors['queryError'] = ['There was a problem executing the query to get the certificate information.']
        return render_template('index.html', jsonList=loadCerts(), environmentList=getEnvironmentTypes(), teamList=getTeamList(), errors=errors)
    
    for row in results:
        if row._mapping.id is id:
            jsonResult = row._mapping
            cert = models.SSLCertModel.SSLCert(jsonResult.id, jsonResult.name, jsonResult.address, jsonResult.port, jsonResult.environment, jsonResult.environmentid, jsonResult.team)

    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        port = request.form['port']
        team = request.form['team']
        environmentid = request.form['environmentSelect']

        if environmentid == 'Choose Environment':
            errors['environmentSelectError'] = ['You did not select an environment.']
            return render_template("editcert.html", environmentList=getEnvironmentTypes(), cert=cert, errors=errors)

        if not validateCert(address, int(port)):
            errors['invalidCertError'] = ['The address and port you provided does not give a valid SSL certificate.']
            return render_template("editcert.html", environmentList=getEnvironmentTypes(), cert=cert, errors=errors)

        query = "UPDATE CertInfo SET name='" + name + "', address='" + address + "', port='" + port + "', team='" + team + "', environmentid=" + str(environmentid) + " WHERE id=" + str(id) + ";"
        try:
            conn = engine.connect()
            conn.execute(text(query))
            conn.commit()
        except:
            engine.dispose()
            app.logger.warning("There was a problem executing the update SSL Cert info query.")
            errors['queryError'] = ['There was a problem executing the update certificate query.']
            return render_template("editcert.html", environmentList=getEnvironmentTypes(), cert=cert, errors=errors)

        app.logger.info("/edit/" + str(id) +" page was called. previousCertInfo={name=" + cert.name + ",address=" + cert.address + ",port=" + str(cert.port) + ",team" + cert.team + ",environmentid=" + str(cert.environmentid) + "} ... newCertInfo={name=" + name + ",address=" + address + ",port=" + port + ",team" + team + ",environmentid=" + str(environmentid) + "} ... from ip=" + request.remote_addr)
        return redirect(url_for('index'))

    return render_template("editcert.html", environmentList=getEnvironmentTypes(), cert=cert, errors=errors)

@app.route('/delete/<int:id>', methods=['GET'])
def delete(id):
    if session.get('email') == None:
        return redirect(url_for('index'))

    errors={}
    query = "DELETE FROM CertInfo WHERE id=" + str(id) + ";"
    try:
        conn = engine.connect()
        conn.execute(text(query))
        conn.commit()
    except:
        engine.dispose()
        app.logger.warning("There was a problem deleting the certificate from the database.")
        errors['deleteQueryError'] = ['There was a problem deleting the certificate from the database.']
        return render_template("index.html", jsonList=loadCerts(), environmentList=getEnvironmentTypes(), teamList=getTeamList(), errors=errors)

    app.logger.info("/delete/"+ str(id) +" was called from ip=" + request.remote_addr)
    return redirect(url_for('index'))

@app.route('/userList')
def userList():
    if session.get('isadmin') == None:
        return redirect(url_for('index'))

    errors={} 
    results = []
    userList = []
    query = "SELECT id, email, isadmin FROM UserInfo;"
    try:
        results = engine.connect().execute(text(query))
    except:
        engine.dispose()
        app.logger.warning("There was a problem executing the user list query.")
        errors['queryError'] = ['There was a problem executing the user list query.']
        return render_template("userList.html", errors=errors)

    for row in results:
        jsonResult = row._mapping
        userList.append(jsonResult)

    app.logger.info("/userList was called from email=" + session['email'] + ", ip=" + request.remote_addr)
    return render_template('userList.html', userList=userList, errors=errors)

@app.route('/deleteUser/<int:id>', methods=['GET'])
def deleteUser(id):
    if session.get('isadmin') == None:
        return redirect(url_for('index'))

    errors={}
    query = "DELETE FROM UserInfo WHERE id=" + str(id) + ";"
    try:
        conn = engine.connect()
        conn.execute(text(query))
        conn.commit()
    except:
        engine.dispose()
        app.logger.warning("There was a problem deleting the user from the database.")
        errors['queryError'] = ['There was a problem deleting the user from the database.']
        return render_template("index.html", jsonList=loadCerts(), environmentList=getEnvironmentTypes(), teamList=getTeamList(), errors=errors)

    app.logger.info("/deleteUser/"+ str(id) +" was called from email=" + session['email'] + ", ip=" + request.remote_addr)
    return redirect(url_for('userList'))

@app.route('/environmentList')
def environmentList():
    if session.get('isadmin') == None:
        return redirect(url_for('index'))

    errors={} 
    results = []
    envList = []
    query = "SELECT * FROM Environment;"
    try:
        results = engine.connect().execute(text(query))
    except:
        engine.dispose()
        app.logger.warning("There was a problem executing the environment list query.")
        errors['queryError'] = ['There was a problem executing the environment list query.']
        return render_template("environmentList.html", errors=errors)

    for row in results:
        jsonResult = row._mapping
        envList.append(jsonResult)

    app.logger.info("/environmentList was called from email=" + session['email'] + ", ip=" + request.remote_addr)
    return render_template('environmentList.html', envList=envList, errors=errors)

@app.route('/addEnvironment', methods=['GET','POST'])
def addEnvironment():
    if session.get('isadmin') == None:
        return redirect(url_for('index'))

    errors={}
    if request.method == 'POST':
        environment = request.form['environment']

        query = "INSERT INTO Environment(environment) VALUES ('" + environment +"');"
        try:
            conn = engine.connect()
            conn.execute(text(query))
            conn.commit()
        except:
            engine.dispose()
            app.logger.warning("There was a problem executing the add environment query.")
            errors['queryError'] = ['There was a problem executing the add environment query.']
            return render_template("addcert.html", environmentList=getEnvironmentTypes(), errors=errors)

        app.logger.info("/add page was called with environment=" + environment + ", and ip =" + request.remote_addr)
        return redirect(url_for('environmentList'))
    
    return render_template("addEnvironment.html", errors=errors)

@app.route('/deleteEnvironment/<int:id>', methods=['GET'])
def deleteEnvironment(id):
    if session.get('isadmin') == None:
        return redirect(url_for('index'))

    errors={}
    query = "DELETE FROM Environment WHERE id=" + str(id) + ";"
    try:
        conn = engine.connect()
        conn.execute(text(query))
        conn.commit()
    except:
        engine.dispose()
        app.logger.warning("There was a problem deleting the environment from the database. It's possible the environment was linked with a certificate and would have caused an error loading its details.")
        errors['queryError'] = ["There was a problem deleting the environment from the database. It's possible the environment was linked with a certificate and would have caused an error loading its details."]
        return render_template("index.html", jsonList=loadCerts(), environmentList=getEnvironmentTypes(), teamList=getTeamList(), errors=errors)

    app.logger.info("/deleteEnvironment/"+ str(id) +" was called from email=" + session['email'] + ", ip=" + request.remote_addr)
    return redirect(url_for('environmentList'))
