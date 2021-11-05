import os
from datetime import datetime
import random
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from markupsafe import Markup
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required
# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = SQL("sqlite:///database.db")

#Start App

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    #logic to pull username
    userID = session["user_id"]
    userReturn = db.execute("SELECT * FROM users WHERE id = ?",userID)
    name = userReturn[0]['username']
    activeGame = int(userReturn[0]['activeGame'])


    if request.method == "POST":
        if request.form.get('createGame'):
            gamePassword = ""
            if request.form.get('gamePassword'):
                gamePassword = request.form.get('gamePassword')
            if activeGame>0:
                return apology("You're already in a game!",403)
            #query database, create new game ID, set owner, playerlist and active game, redirect to game
            listID = db.execute("SELECT gameID FROM games")
            if listID:
                lastGameID = listID[-1]['gameID']
            else:
                lastGameID = 0
            playerList = []
            playerList.append(userID)
            db.execute("INSERT INTO games (gameID,ownerName,ownerID,playerList,playerCount,active,password,started) VALUES(?, ?, ?, ?, ?, ?, ?,?)" , (lastGameID+1),name,userID,str(playerList),1,1,gamePassword,0)
            db.execute("UPDATE users SET activeGame = ? WHERE id = ?",(lastGameID+1),userID)

            return redirect("/join")


        if request.form.get('joinGame'):
            gamePassword = ""
            if request.form.get('gamePassword'):
                gamePassword = request.form.get('gamePassword')
            #set playerlist, active game, redirect to game
            gameID = request.form.get('joinGame')
            gameInfo = db.execute("SELECT * FROM games WHERE gameID = ?",gameID)
            gameInfo = gameInfo[0]
            if gamePassword != gameInfo['password']:
                return apology("Wrong Password!",403)
            playerCount = gameInfo['playerCount']
            if playerCount > 9:
                return apology("Game full!",403)
            if activeGame>0:
                return apology("You're already in a game!",403)
            playerList = rebuildList(gameInfo['playerList'])
            playerList.append(userID)
            db.execute("UPDATE users SET activeGame = ? WHERE id = ?",gameID,userID)
            db.execute("UPDATE games SET playerList = ? WHERE gameID = ?",str(playerList),gameID)
            playerCount = db.execute("SELECT playerCount FROM games WHERE gameID = ?",gameID)
            playerCount = int(playerCount[0]['playerCount'])
            db.execute("UPDATE games SET playerCount = ? WHERE gameID = ?",(playerCount+1),gameID)



            return redirect("/join")


        activeGames = db.execute("SELECT * FROM games WHERE (active = 1 and started = 0)")
        if request.form.get('refreshGames'):
            return render_template("index.html",username = name, games = activeGames, activeGame = activeGame)


    else:
        activeGames = db.execute("SELECT * FROM games WHERE (active = 1 and started = 0)")
        return render_template("index.html",username = name, games = activeGames, activeGame = activeGame)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        countQuery = db.execute("SELECT COUNT(*) FROM users;")[0]
        l = list(countQuery)
        count = int(countQuery[l[0]]) + 1
        username = request.form.get("username")
        if not username:
            return apology("Empty field!",400)
        password = request.form.get("password")
        if not password:
            return apology("Empty field!",400)
        confirmpassword = request.form.get("confirmation")
        if not confirmpassword:
            return apology("Empty field!",400)
        if password != confirmpassword:
            return apology("Passwords much match!")
        hashed = generate_password_hash(password)
        allUsers = db.execute("SELECT username FROM users")
        for item in allUsers:
            iUser = list(item.values())
            if iUser[0] == username:
                return apology("Username taken!", 400)
        db.execute("INSERT INTO users (id,username,hash,activeGame) VALUES(?, ?, ?,?)",count,username,hashed,0)

        #return render_template("login.html")
        #Log user in automatically
        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    else:
        return render_template("register.html")
        #GET method

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@login_required
@app.route("/join")
def join():
    """Join Game"""
    if not session:
        return redirect("/")
    if not session["user_id"]:
        return redirect("/")
    userID = session["user_id"]
    userReturn = db.execute("SELECT * FROM users WHERE id = ?",userID)
    name = userReturn[0]['username']
    activeGame = int(userReturn[0]['activeGame'])
    if not activeGame:
        return redirect("/")
    else:
        return redirect("/game")
    #if player has active game direct them
    #else redirect them home
@login_required
@app.route("/leave")
def leave():
    """Leave/end empty or middle game"""
    userID = session["user_id"]
    userReturn = db.execute("SELECT * FROM users WHERE id = ?",userID)
    name = userReturn[0]['username']
    activeGame = userReturn[0]['activeGame']
    gameReturn = db.execute("SELECT * FROM games WHERE gameID = ?",activeGame)
    gameReturn = gameReturn[0]
    if gameReturn['started']:
        db.execute("DELETE * FROM playerDetails WHERE gameID = ?",gameReturn['gameID'])
        db.execute("UPDATE games SET active=?,started=? WHERE gameID = ?",0,0,gameReturn['gameID'])
    playerList = rebuildList(gameReturn['playerList'])
    count = gameReturn['playerCount']
    if count <= 1:
        db.execute("UPDATE games SET active = 0 WHERE gameID = ?",activeGame)
    playerList.remove(userID)
    db.execute("UPDATE users SET activeGame = ? WHERE id = ?",0,userID)
    db.execute("DELETE FROM playerDetails WHERE playerID = ?",userID)
    db.execute("UPDATE games SET playerCount = ?, playerList = ? WHERE gameID = ?",(count-1),str(playerList),activeGame)

    return redirect("/")

@login_required
@app.route("/game", methods=["GET", "POST"])
def game():
    """Game page first load"""
    userID = session["user_id"]
    userReturn = db.execute("SELECT * FROM users WHERE id = ?",userID)
    userReturn = userReturn[0]
    name = userReturn['username']
    activeGame = int(userReturn['activeGame'])
    gameReturn = db.execute("SELECT * FROM games WHERE gameID = ?",activeGame)
    gameReturn = gameReturn[0]
    #Got all the basic info from the database
    gameDetailsReturn = db.execute("SELECT * FROM details WHERE gameID = ?",activeGame)
    if not gameDetailsReturn:
        if userReturn['id'] == gameReturn['ownerID']:
            startButton = True
        else:
            startButton = False
    else:
        startButton = False
    if gameReturn['started']:
        startButton = False
        playerDetailsReturn = db.execute("SELECT * FROM playerDetails WHERE playerID = ?",userID)
        if playerDetailsReturn:
            playerDetailsReturn = playerDetailsReturn[0]

    playersIDList = rebuildList(gameReturn['playerList'])
    namesList = []
    for i in playersIDList:
        x = db.execute("SELECT username FROM users WHERE id = ?",i)
        if x:
            namesList.append(x[0]["username"])
    tmp = []
    for i in namesList:
        if i not in tmp:
            tmp.append(i)
    namesList = tmp


    if request.method == "POST":

        if request.form.get("startGame"):
            #owner pushed start game button
            startGame(namesList,activeGame)
        if gameReturn['started']:
            startButton = False
            playerDetailsReturn = db.execute("SELECT * FROM playerDetails WHERE playerID = ?",userID)
            playerDetailsReturn = playerDetailsReturn[0]
        #Gamestates for POST method
        if gameReturn['started']:
            #Gameplay
            gameDetails = parseGame()
            playerDetailsReturn = parseActivePlayer()
            role = playerDetailsReturn['playerRole'].upper()


            #Game States
            gameDetails = parseGame()
            state = gameDetails['turnState']
            if state == 0:
                if request.form.get("playerbutton"):
                    print(request.form.get("playerbutton"))
                    if playerDetailsReturn['isPres']:
                        nominee = request.form.get("playerbutton")
                        nomineeDetails = parsePlayerName(nominee)
                        db.execute("UPDATE playerDetails SET nominated = ? WHERE playerID = ?",1,nomineeDetails['playerID'])
                        db.execute("UPDATE details SET turnState = ? WHERE gameID = ?",1,gameDetails['gameID'])
                    else:
                        print("NOT A VOTE")
                return state0()

            elif state == 1:
                #run election logic here
                nomineeInfo = ""
                if not playerDetailsReturn['hasVoted']:
                    for name in namesList:
                        player = parsePlayerName(name)
                        if player['nominated']:
                            nomineeInfo = player
                    if request.form.get("ja"):
                        db.execute("UPDATE details SET jaVotes = ? WHERE gameID = ?",(gameDetails['jaVotes']+1),gameDetails['gameID'])
                        print("!!!! YES VOTE RECORDED\n\n!!!!!!")
                        print(gameDetails['jaVotes'])
                        db.execute("UPDATE playerDetails SET hasVoted = ? WHERE playerID = ?",1,playerDetailsReturn['playerID'])
                    if request.form.get("nein"):
                        db.execute("UPDATE details SET jaVotes = ? WHERE gameID = ?",(gameDetails['neinVotes']+1),gameDetails['gameID'])
                        db.execute("UPDATE playerDetails SET hasVoted = ? WHERE playerID = ?",1,playerDetailsReturn['playerID'])
                total = db.execute("SELECT * FROM details WHERE gameID = ?",(gameDetails['gameID']))
                total = total[0]
                if total['jaVotes']+total['neinVotes'] == gameDetails['playersAlive']:
                    db.execute("UPDATE playerDetails SET hasVoted = ?",0) #clear out voted status
                    if total['jaVotes'] > total['neinVotes']:
                        pass
                        #goto state 3 win!
                        db.execute("UPDATE playerDetails SET isChan = ? WHERE playerID = ?",1,playerDetailsReturn['playerID'])
                        db.execute("UPDATE details SET turnState = ? WHERE gameID = ?",3,gameDetails['gameID'])

                    else:
                        #goto state 2
                        db.execute("UPDATE details SET turnState = ? WHERE gameID = ?",2,gameDetails['gameID'])

                return state1()
            elif state == 2:
                return state2()
            elif state == 3:
                gameDetails = parseGame()
                playerDetails = parseActivePlayer()
                namesList = getNameList()
                playerStatus(namesList,gameDetails['gameID'])
                name = getOwnUsername()
                startButton=False
                role = playerDetails['playerRole'].upper()
                for name in namesList:
                    player = parsePlayerName(name)
                    #check win conditions
                    if player['isChan']:
                        if player['playerRole'] == "hitler":
                            if gameDetails['fpolicies'] > 2:
                                #win condition
                                pass
                    if player['isPres']:
                        president = player
                if playerDetails['isPres']:
                    if request.form.get("fascist"):
                        #delete fascist policy
                        hand = repairList(gameDetails['policyHand'])
                        hand.remove(1)
                        for i in range(0,2):
                            p = l.pop()
                            policies.append(p)
                        db.execute("UPDATE details SET policyHand = ? WHERE gameID = ?",policies,gameDetails['gameID'])
                        db.execute("UPDATE details SET turnState = ? WHERE gameID = ?",4,gameDetails['gameID'])
                        return state4()
                    elif request.form.get("liberal"):
                        #delete liberal policy
                        hand = repairList(gameDetails['policyHand'])
                        hand.remove(0)
                        for i in range(0,2):
                            p = l.pop()
                            policies.append(p)
                        db.execute("UPDATE details SET policyHand = ? WHERE gameID = ?",policies,gameDetails['gameID'])
                        db.execute("UPDATE details SET turnState = ? WHERE gameID = ?",4,gameDetails['gameID'])
                        return state4()
                #draw policies
                if not gameDetails['policyHand']:
                    policies = []
                    l = rebuildList(gameDetails['deck'])
                    #if less than 3, shuffle
                    if len(l) < 3:
                        lpolicies = 6-gameDetails['lpolicies']
                        fpolicies = 11-gameDetails['fpolicies']
                        newDeck = []
                        for i in range(0,lpolicies):
                            newDeck.append(0)
                        for i in range(0,fpolicies):
                            newDeck.append(1)
                        db.execute("UPDATE details SET deck = ? WHERE gameID = ?",newDeck,gameDetails['gameID'])
                        gameDetails = parseGame()
                        l = rebuildList(gameDetails['deck'])
                    #draw 3
                    for i in range(0,3):
                        p = l.pop()
                        policies.append(p)
                    db.execute("UPDATE details SET deck = ? WHERE gameID = ?",l,gameDetails['gameID'])
                    db.execute("UPDATE details SET policyHand = ? WHERE gameID = ?",policies,gameDetails['gameID'])
                    return state3()
                else:
                    state3()
            elif state == 4:
                gameDetails = parseGame()
                playerDetails = parseActivePlayer()
                namesList = getNameList()
                playerStatus(namesList,gameDetails['gameID'])
                name = getOwnUsername()
                startButton=False
                role = playerDetails['playerRole'].upper()
                for name in namesList:
                    player = parsePlayerName(name)
                    if player['isChan']:
                        chan = player
                    if player['isPres']:
                        president = player
                if playerDetails['isChan']:
                    if request.form.get("fascist"):
                        #remove fascist policy
                        hand = repairList(gameDetails['policyHand'])
                        hand.remove(1)
                        db.execute("UPDATE details SET policyHand = ? WHERE gameID = ?",hand,gameDetails['gameID'])
                        db.execute("UPDATE details SET turnState = ? WHERE gameID = ?",6,gameDetails['gameID'])
                        return state6()
                    elif request.form.get("liberal"):
                        #remove liberal policy
                        hand = repairList(gameDetails['policyHand'])
                        hand.remove(0)
                        db.execute("UPDATE details SET policyHand = ? WHERE gameID = ?",hand,gameDetails['gameID'])
                        db.execute("UPDATE details SET turnState = ? WHERE gameID = ?",6,gameDetails['gameID'])
                        return state6()
                    elif request.form.get("veto"):
                        db.execute("UPDATE details SET turnState = ? WHERE gameID = ?",5,gameDetails['gameID'])
                        return state5()
                else:
                    state4()
            elif state == 5:
                gameDetails = parseGame()
                playerDetails = parseActivePlayer()
                namesList = getNameList()
                playerStatus(namesList,gameDetails['gameID'])
                name = getOwnUsername()
                startButton=False
                role = playerDetails['playerRole'].upper()
                highest = 0
                for name in namesList:
                    player = parsePlayerName(name)
                    if player['isChan']:
                        chan = player
                    if player['isPres']:
                        president = player
                    if player['turnOrder'] > highest:
                        highest = player['turnOrder']
                if playerDetails['isPres']:
                    if request.form.get("veto"):
                        db.execute("UPDATE details SET turnState = ? WHERE gameID = ?",0,gameDetails['gameID'])
                        failed = gameDetails['failedVotes'] + 1
                        rotation = gameDetails['turnRotation']
                        if rotation == highest:
                            rotation = 0
                        else:
                            rotation += 1
                        db.execute("UPDATE details SET failedVotes = ? WHERE gameID = ?",failed,gameDetails['gameID'])
                        db.execute("UPDATE details SET turnRotation = ? WHERE gameID = ?",rotation,gameDetails['gameID'])
                        for name in namesList:
                            player = parsePlayerName(name)
                            if player['isChan']:
                                db.execute("UPDATE playerDetails SET isElig = ? WHERE gameID = ?",0,player['playerID'])
                            if player['isPres']:
                                db.execute("UPDATE playerDetails SET isElig = ? WHERE gameID = ?",0,player['playerID'])
                        state0()
                else:
                    #President denies veto
                    db.execute("UPDATE details SET turnState = ? WHERE gameID = ?",4,gameDetails['gameID'])
            elif state == 6:
                gameDetails = parseGame()
                playerDetails = parseActivePlayer()
                namesList = getNameList()
                playerStatus(namesList,gameDetails['gameID'])
                name = getOwnUsername()
                startButton=False
                role = playerDetails['playerRole'].upper()
                policy = gameDetails['policyHand']
                lpol = gameDetails['lpolicies']
                fpol = gameDetails['fpolicies']
                if policy[0] == 1:
                    db.execute("UPDATE details SET lpolicies = ? WHERE gameID = ?",lpol+1,gameDetails['gameID'])
                if policy[0] == 0:
                    db.execute("UPDATE details SET fpolicies = ? WHERE gameID = ?",fpol+1,gameDetails['gameID'])
                #TODO special actions

                #otherwise, new turn
                db.execute("UPDATE details SET turnState = ? WHERE gameID = ?",0,gameDetails['gameID'])
                rotation = gameDetails['turnRotation']
                if rotation == highest:
                    rotation = 0
                else:
                    rotation += 1
                db.execute("UPDATE details SET failedVotes = ? WHERE gameID = ?",failed,gameDetails['gameID'])
                db.execute("UPDATE details SET turnRotation = ? WHERE gameID = ?",rotation,gameDetails['gameID'])
                for name in namesList:
                    player = parsePlayerName(name)
                    if player['isChan']:
                        db.execute("UPDATE playerDetails SET isElig = ? WHERE gameID = ?",0,player['playerID'])
                    if player['isPres']:
                        db.execute("UPDATE playerDetails SET isElig = ? WHERE gameID = ?",0,player['playerID'])
                state0()
            elif state == 7:
                pass
            elif state == 8:
                pass
            elif state == 9:
                pass
            elif state == 10:
                pass
            elif state == 11:
                pass
        print(gameReturn)
        return render_template("game.html", username = name, activeGame = activeGame, inGame = True,
        players = namesList, playerStatus = playerStatus(namesList,activeGame) ,jumbo = jumbotronDisplay(bigTitle="Starting...Please Refresh"),startButton=False,boardStatus=False)

    else:
        if gameReturn['started']:
            #Gameplay
            gameDetails = parseGame()
            playerDetailsReturn = parseActivePlayer()
            if playerDetailsReturn:
                role = playerDetailsReturn['playerRole'].upper()
            else:
                role = "pending..."

            #Game States
            gameDetails = parseGame()
            if gameDetails:
                state = gameDetails['turnState']
            else:
                state = -1
            if state == 0:
                return state0()
            elif state == 1:
                return state1()
            elif state == 2:
                return state2()
            elif state == 3:
                return state3()
            elif state == 4:
                return state4()
            elif state == 5:
                return state5()
            elif state == 6:
                return state6()
            elif state == 7:
                pass
            elif state == 8:
                pass
            elif state == 9:
                pass
            elif state == 10:
                pass
            elif state == 11:
                pass


            if role != "pending...":
            #else: just render game
                return render_template("game.html", username = name, activeGame = activeGame, inGame = True,
                players = namesList, playerStatus = playerStatus(namesList,activeGame) ,jumbo = jumbotronDisplay(bigTitle="Started",secondaryTitle="You are a {}!".format(role)),startButton=startButton,
                boardStatus=boardDisplay(gameDetails["lpolicies"],gameDetails['fpolicies'],gameDetails['gameID'])
                ,showButtons=True)


        return render_template("game.html", username = name, activeGame = activeGame, inGame = True,
        players = namesList, playerStatus = playerStatus(namesList,activeGame) ,jumbo = jumbotronDisplay(bigTitle="Waiting to start"),startButton=True,boardStatus=False)








def startGame(namesList,activeGame):
    playerDict = {}
    for name in namesList:
        response = db.execute("SELECT * FROM users WHERE username = ?",name)
        playerDict[name] = response[0]
    gameReturn = db.execute("SELECT * FROM games WHERE gameID = ?",activeGame)
    gameReturn = gameReturn[0]
    #pulled all info from DB

    #assign teams
    tmplist = namesList.copy()
    hitler = tmplist.pop(random.randint(0,len(tmplist)-1))
    fascists = []
    if len(namesList) < 7:
        fascists.append(tmplist.pop(random.randint(0,len(tmplist)-1)))
    elif len(namesList) < 9:
        fascists.append(tmplist.pop(random.randint(0,len(tmplist)-1)))
        fascists.append(tmplist.pop(random.randint(0,len(tmplist)-1)))
    else:
        fascists.append(tmplist.pop(random.randint(0,len(tmplist)-1)))
        fascists.append(tmplist.pop(random.randint(0,len(tmplist)-1)))
        fascists.append(tmplist.pop(random.randint(0,len(tmplist)-1)))

    deck = [1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0]
    random.shuffle(deck)

    #update all games,playerDetails,details
    totalPlayers = gameReturn['playerCount']
    db.execute("UPDATE games SET started = ? WHERE gameID = ?",1,gameReturn['gameID'])


    db.execute("INSERT INTO details (gameID , gameSize , winner , deck , policyHand, playersAlive ) VALUES(?,?,?,?,?,?)",
    gameReturn['gameID'],totalPlayers,"",str(deck),"",totalPlayers)

    #pick first president
    randn = random.randint(0,len(namesList)-1)
    pres = namesList[randn]

    #assign roles in DB
    n = randn
    db.execute("UPDATE details SET turnRotation = ? WHERE gameID = ?",n,activeGame)
    for name in namesList:
        playerInfo = playerDict[name]
        isPres = 0
        if name == pres:
            isPres = 1
        role = ""
        if name == hitler:
            role = "hitler"
        elif name in fascists:
            role = "fascist"
        else:
            role = "liberal"
        db.execute("INSERT INTO playerDetails (playerID ,gameID , playerRole , turnOrder, isPres) VALUES(?, ?, ?, ?,?)",
        playerInfo['id'],gameReturn['gameID'],role,n,isPres)
        if n == totalPlayers:
            n = 0
        else:
            n+=1


    return





def rebuildList(s):
    if s == "None":
        return []
    out = []
    s = s[1:-1]
    s = s.split(",")
    for num in s:
        num = int(num)
        out.append(num)
    return out


def playerStatus(namesList,activeGame):
    #text for dead,alive,chancellor,fascist,hitler
    #check is current session is fascist player, then display accordingly
    #account for 5 person game
    outDict = {}
    gameDetailsReturn = db.execute("SELECT * FROM details WHERE gameID = ?",activeGame)
    #game hasn't started
    if not gameDetailsReturn:
        print(gameDetailsReturn)
        print("!!!!!!!!!!")
        for name in namesList:
            playerDict = {}
            playerDict['button'] = "btn btn-info"
            playerDict['title'] = ""
            outDict[name] = playerDict
    else:
        #Update game based on view (no filter for liberals yet)
        for name in namesList:
            playerDict = {}
            playerID = db.execute("SELECT * FROM users WHERE username = ?",name)
            playerID = playerID[0]["id"]
            playerDetails = db.execute("SELECT * FROM playerDetails WHERE playerID = ?",playerID)
            playerDetails = playerDetails[0]
            #needs filtering for non-fascist team
            if not playerDetails['alive']:
                playerDict['button'] = "btn btn-dark"
            elif playerDetails['playerRole'] == 'hitler':
                playerDict['button'] = "btn btn-danger"
            elif playerDetails['playerRole'] == 'fascist':
                playerDict['button'] = "btn btn-warning"
            else:
                playerDict['button'] = "btn btn-primary"

            if not playerDetails["isElig"]:
                playerDict['title'] = "Term Limited: "
            elif playerDetails['isPres']:
                playerDict['title'] = "President "
            elif playerDetails['isChan']:
                playerDict['title'] = "Chancellor "
            outDict[name] = playerDict
    print(outDict)
    return outDict



def jumbotronDisplay(bigTitle="",secondaryTitle="",normalText="",showButtons=False,showVeto=False,policies=[]):
    #policies is a list that is converted to dict. Leave empty if not used
    #showButtons is bool
    policyDict = {}
    if policies:
        for i in range(0,len(policies)):
            policyDict[i] = policies[i]
    out = {
        "header":bigTitle,
        "secondary":secondaryTitle,
        "text":normalText,
        "showButtons":showButtons,
        "policies":policyDict,
        "showVeto":showVeto

    }
    return out

def boardDisplay(liberal,fascist,gameID):
    gameInfo = db.execute("SELECT * FROM details WHERE gameID = ?",gameID)
    gameInfo = gameInfo[0]
    gameSize = gameInfo['gameSize']
    tracker = gameInfo['failedVotes']
    outDict = {
        "liberal":"",
        "fascist":""
    }
    if gameSize > 8:
        #10-9 people
        outDict['liberal'] = "liberalboards" + "/tracker" + str(tracker) + "/liberal" + str(liberal) + ".png"
        outDict['fascist'] = "10players/10players" + str(fascist) + ".png"
    elif gameSize > 6:
        #8-7 people
        outDict['liberal'] = "liberalboards" + "/tracker" + str(tracker) + "/liberal" + str(liberal) + ".png"
        outDict['fascist'] = "8players/8players" + str(fascist) + ".png"
    else:
        outDict['liberal'] = "liberalboards" + "/tracker" + str(tracker) + "/liberal" + str(liberal) + ".png"
        outDict['fascist'] = "6players/6players" + str(fascist) + ".png"
        #6-5 people
    return outDict


"""

SQL turn states:
0 President- waiting for nomination, person after previous president if not first time.
1 Chancellor choosen- election- wait for votes
2 Failed, advance tracker and go back to 0, or if chaos random policy 6 and reset tracker
3 Elected- check if Chancellor is Hitler if 3 fpolicies else give Pres 3 policies from deck and update deck. Shuffle is deck len < 3
4 President choose. Chancellor gets 2 policies. If 5 fpolicies, veto option to 5.
5 If veto choose, let President agree or disagree. If agree to go 0. Otherwise, Chancellor policy is enacted
6 Enact policy- display text about policy. Check if game should be over. Check if goverment has power to use and go to power used.
7 Investigation then to 0
8 Special election- double check logic goes back to regular rotation after
9 Policy peek then to 0
10 Execution then to 0- kill off player, double check logic and database are correctly updated, and turn rotation is kept.
11 Victory screen

"""

def parseGame():
    userID = session["user_id"]
    userReturn = db.execute("SELECT * FROM users WHERE id = ?",userID)
    if not userReturn:
        print("NO ACTIVE GAME!!!")
        return
    userReturn = userReturn[0]
    gameID = userReturn['activeGame']
    gameDetails = db.execute("SELECT * FROM details WHERE gameID = ?",gameID)
    if gameDetails:
        gameDetails = gameDetails[0]
    return gameDetails

def parseActivePlayer():
    userID = session["user_id"]
    userReturn = db.execute("SELECT * FROM users WHERE id = ?",userID)
    if not userReturn:
        print("NO ACTIVE GAME FOR USER!!!")
        return
    userReturn = userReturn[0]
    playerID = userReturn['id']
    playerDetails = db.execute("SELECT * FROM playerDetails WHERE playerID = ?",playerID)
    if playerDetails:
        playerDetails = playerDetails[0]
    return playerDetails

def parsePlayerName(name):
    userReturn = db.execute("SELECT * FROM users WHERE username = ?",name)
    if not userReturn:
        print("NO ACTIVE GAME FOR USER!!!")
        return
    userReturn = userReturn[0]
    playerID = userReturn['id']
    playerDetails = db.execute("SELECT * FROM playerDetails WHERE playerID = ?",playerID)
    playerDetails = playerDetails[0]
    return playerDetails

def parsePlayerID(playerID):
    userReturn = db.execute("SELECT * FROM users WHERE playerID = ?",playerID)
    if not userReturn:
        print("NO ACTIVE GAME FOR USER!!!")
        return
    userReturn = userReturn[0]
    playerID = userReturn['id']
    playerDetails = db.execute("SELECT * FROM playerDetails WHERE playerID = ?",playerID)
    playerDetails = playerDetails[0]
    return playerDetails

def getOwnUsername():
    userID = session["user_id"]
    userReturn = db.execute("SELECT * FROM users WHERE id = ?",userID)
    name = userReturn[0]['username']
    return name


def getNameList():
    userID = session["user_id"]
    userReturn = db.execute("SELECT * FROM users WHERE id = ?",userID)
    if not userReturn:
        print("NO ACTIVE GAME!!!")
        return
    userReturn = userReturn[0]
    gameID = userReturn['activeGame']
    gameReturn = db.execute("SELECT * FROM games WHERE gameID = ?",gameID)
    gameReturn = gameReturn[0]
    playersIDList = rebuildList(gameReturn['playerList'])
    namesList = []
    for i in playersIDList:
        x = db.execute("SELECT username FROM users WHERE id = ?",i)
        if x:
            namesList.append(x[0]["username"])
    tmp = []
    for i in namesList:
        if i not in tmp:
            tmp.append(i)
    namesList = tmp
    return namesList




#DISPLAY functions

def state0():
    #0 President- waiting for nomination, person after previous president if not first time.
    gameDetails = parseGame()
    playerDetails = parseActivePlayer()
    namesList = getNameList()
    playerStatus(namesList,gameDetails['gameID'])
    name = getOwnUsername()
    startButton=False
    role = playerDetails['playerRole'].upper()
    gameRound = gameDetails['turnRotation'] + 1


    #All display variables needed-done
    if playerDetails['isPres']:
        return render_template("game.html", username = name, activeGame = gameDetails['gameID'], inGame = True,
            players = namesList, playerStatus = playerStatus(namesList,gameDetails['gameID']) ,jumbo = jumbotronDisplay(bigTitle="President Nomination!",secondaryTitle="Double Click on a user to nominate them for Chancellor".format(role)),startButton=startButton,
            boardStatus=boardDisplay(gameDetails["lpolicies"],gameDetails['fpolicies'],gameDetails['gameID'])
            ,showButtons=True)
    else:
        return render_template("game.html", username = name, activeGame = gameDetails['gameID'], inGame = True,
            players = namesList, playerStatus = playerStatus(namesList,gameDetails['gameID']) ,jumbo = jumbotronDisplay(bigTitle="President Nomination!",secondaryTitle="Waiting for President...Please refresh occasionally".format(role)),startButton=startButton,
            boardStatus=boardDisplay(gameDetails["lpolicies"],gameDetails['fpolicies'],gameDetails['gameID'])
            ,showButtons=True)

def state1():
    #1 Chancellor choosen- election- wait for votes
    gameDetails = parseGame()
    playerDetails = parseActivePlayer()
    namesList = getNameList()
    playerStatus(namesList,gameDetails['gameID'])
    name = getOwnUsername()
    startButton=False
    role = playerDetails['playerRole'].upper()
    gameRound = gameDetails['turnRotation'] + 1
    president = ""
    nominee = ""
    for name in namesList:
        player = parsePlayerName(name)
        if player['nominated']:
            nominee = name
        if player['isPres']:
            president = name

    if playerDetails['hasVoted']:
        return render_template("game.html", username = name, activeGame = gameDetails['gameID'], inGame = True,
                players = namesList, playerStatus = playerStatus(namesList,gameDetails['gameID']) ,jumbo = jumbotronDisplay(showButtons = False,
                bigTitle="Chancellor Nomination!",secondaryTitle="Vote Recorded".format(role)),startButton=startButton,
                boardStatus=boardDisplay(gameDetails["lpolicies"],gameDetails['fpolicies'],gameDetails['gameID'])
                ,showButtons=True)
    else:
        return render_template("game.html", username = name, activeGame = gameDetails['gameID'], inGame = True,
                players = namesList, playerStatus = playerStatus(namesList,gameDetails['gameID']) ,jumbo = jumbotronDisplay(showButtons = True,
                bigTitle="Chancellor Nomination",normalText = "President {} and Chancellor {} attempt to form a goverment!".format(president,nominee),secondaryTitle="Vote!".format(role)),startButton=startButton,
                boardStatus=boardDisplay(gameDetails["lpolicies"],gameDetails['fpolicies'],gameDetails['gameID'])
                ,showButtons=True)

def state2():
    #2 Failed, advance tracker and go back to 0, or if chaos random policy 6 and reset tracker
    gameDetails = parseGame()
    playerDetails = parseActivePlayer()
    namesList = getNameList()
    playerStatus(namesList,gameDetails['gameID'])
    name = getOwnUsername()
    startButton=False
    role = playerDetails['playerRole'].upper()
    gameRound = gameDetails['turnRotation'] + 1
    president = {}
    nominee = {}
    for name in namesList:
        player = parsePlayerName(name)
        if player['nominated']:
            nominee = player
        if player['isPres']:
            president = player
    previousTurn = president['turnOrder']
    nextTurn = previousTurn + 1
    if gameDetails['failedVotes'] == 3:
        #choas-implement random policy. TODO
        pass
    else:
        db.execute("UPDATE details SET failedVotes = ? , turnRotation = ?, turnState = ? WHERE gameID = ?",(gameDetails['failedVotes']+1), nextTurn, 0, gameDetailed['gameID'])
    return redirect("/game")

def state3():
    #3 Elected- check if Chancellor is Hitler if 3 fpolicies else give Pres 3 policies from deck and update deck. Shuffle is deck len < 3
    gameDetails = parseGame()
    playerDetails = parseActivePlayer()
    namesList = getNameList()
    playerStatus(namesList,gameDetails['gameID'])
    name = getOwnUsername()
    startButton=False
    role = playerDetails['playerRole'].upper()
    if gameDetails['policyHand']:
        policiesRaw = rebuildList(gameDetails['policyHand'])
    else:
        policiesRaw = []
    policies = []
    for n in policiesRaw:
        if n:
            policies.append("liberal")
        else:
            policies.append("fascist")
    if playerDetails['isPres']:
        return render_template("game.html", username = name, activeGame = gameDetails['gameID'], inGame = True,
                players = namesList, playerStatus = playerStatus(namesList,gameDetails['gameID']) ,jumbo = jumbotronDisplay(showButtons = False,
                bigTitle="Policy Session",secondaryTitle="Choose a policy to discard",policies = policies)
                ,startButton=startButton,
                boardStatus=boardDisplay(gameDetails["lpolicies"],gameDetails['fpolicies'],gameDetails['gameID'])
                ,showButtons=True)
    elif playerDetails['isChan']:
        return render_template("game.html", username = name, activeGame = gameDetails['gameID'], inGame = True,
                players = namesList, playerStatus = playerStatus(namesList,gameDetails['gameID']) ,jumbo = jumbotronDisplay(showButtons = False,
                bigTitle="Policy Session",secondaryTitle="Waiting for President"),startButton=startButton,
                boardStatus=boardDisplay(gameDetails["lpolicies"],gameDetails['fpolicies'],gameDetails['gameID'])
                ,showButtons=True)
    else:
        return render_template("game.html", username = name, activeGame = gameDetails['gameID'], inGame = True,
                players = namesList, playerStatus = playerStatus(namesList,gameDetails['gameID']) ,jumbo = jumbotronDisplay(showButtons = True,
                bigTitle="Policy Session",normalText = "Waiting for president"),startButton=startButton,
                boardStatus=boardDisplay(gameDetails["lpolicies"],gameDetails['fpolicies'],gameDetails['gameID'])
                ,showButtons=True)


def state4():
    #4 President choose. Chancellor gets 2 policies. If 5 fpolicies, veto option to 5.
    gameDetails = parseGame()
    playerDetails = parseActivePlayer()
    namesList = getNameList()
    playerStatus(namesList,gameDetails['gameID'])
    name = getOwnUsername()
    startButton=False
    role = playerDetails['playerRole'].upper()
    policiesRaw = rebuildList(gameDetails['policyHand'])
    policies = []
    for n in policiesRaw:
        if n:
            policies.append("liberal")
        else:
            policies.append("fascist")
    if playerDetails['isChan']:
        return render_template("game.html", username = name, activeGame = gameDetails['gameID'], inGame = True,
                players = namesList, playerStatus = playerStatus(namesList,gameDetails['gameID']) ,jumbo = jumbotronDisplay(showButtons = False,
                bigTitle="Policy Session",secondaryTitle="Choose a policy to discard",policies = policies,showVeto=True)
                ,startButton=startButton,
                boardStatus=boardDisplay(gameDetails["lpolicies"],gameDetails['fpolicies'],gameDetails['gameID'])
                ,showButtons=True)
    elif playerDetails('isPres'):
        return render_template("game.html", username = name, activeGame = gameDetails['gameID'], inGame = True,
                players = namesList, playerStatus = playerStatus(namesList,gameDetails['gameID']) ,jumbo = jumbotronDisplay(showButtons = False,
                bigTitle="Policy Session",secondaryTitle="Waiting for Chancellor"),startButton=startButton,
                boardStatus=boardDisplay(gameDetails["lpolicies"],gameDetails['fpolicies'],gameDetails['gameID'])
                ,showButtons=True)
    else:
        return render_template("game.html", username = name, activeGame = gameDetails['gameID'], inGame = True,
                players = namesList, playerStatus = playerStatus(namesList,gameDetails['gameID']) ,jumbo = jumbotronDisplay(showButtons = True,
                bigTitle="Policy Session",normalText = "Waiting for president"),startButton=startButton,
                boardStatus=boardDisplay(gameDetails["lpolicies"],gameDetails['fpolicies'],gameDetails['gameID'])
                ,showButtons=True)


def state5():
    #5 If veto choose, let President agree or disagree. If agree to go 0. Otherwise, Chancellor policy is enacted
    gameDetails = parseGame()
    playerDetails = parseActivePlayer()
    namesList = getNameList()
    playerStatus(namesList,gameDetails['gameID'])
    name = getOwnUsername()
    startButton=False
    role = playerDetails['playerRole'].upper()
    if playerDetails['isPres']:
        return render_template("game.html", username = name, activeGame = gameDetails['gameID'], inGame = True,
                players = namesList, playerStatus = playerStatus(namesList,gameDetails['gameID']) ,jumbo = jumbotronDisplay(showButtons = True,
                bigTitle="Policy Session",secondaryTitle="Do you agree to veto?")
                ,startButton=startButton,
                boardStatus=boardDisplay(gameDetails["lpolicies"],gameDetails['fpolicies'],gameDetails['gameID'])
                ,showButtons=True)
    elif playerDetails('isChan'):
        return render_template("game.html", username = name, activeGame = gameDetails['gameID'], inGame = True,
                players = namesList, playerStatus = playerStatus(namesList,gameDetails['gameID']) ,jumbo = jumbotronDisplay(showButtons = False,
                bigTitle="Policy Session",secondaryTitle="Waiting for President"),startButton=startButton,
                boardStatus=boardDisplay(gameDetails["lpolicies"],gameDetails['fpolicies'],gameDetails['gameID'])
                ,showButtons=True)
    else:
        return render_template("game.html", username = name, activeGame = gameDetails['gameID'], inGame = True,
                players = namesList, playerStatus = playerStatus(namesList,gameDetails['gameID']) ,jumbo = jumbotronDisplay(showButtons = True,
                bigTitle="Policy Session",normalText = "Chancellor has moved to veto!"),startButton=startButton,
                boardStatus=boardDisplay(gameDetails["lpolicies"],gameDetails['fpolicies'],gameDetails['gameID'])
                ,showButtons=True)

def state6():
    gameDetails = parseGame()
    playerDetails = parseActivePlayer()
    namesList = getNameList()
    playerStatus(namesList,gameDetails['gameID'])
    name = getOwnUsername()
    startButton=False
    role = playerDetails['playerRole'].upper()
    return render_template("game.html", username = name, activeGame = gameDetails['gameID'], inGame = True,
                players = namesList, playerStatus = playerStatus(namesList,gameDetails['gameID']) ,jumbo = jumbotronDisplay(showButtons = False,
                bigTitle="Policy Enactment",normalText = "Policy Played!"),startButton=startButton,
                boardStatus=boardDisplay(gameDetails["lpolicies"],gameDetails['fpolicies'],gameDetails['gameID'])
                ,showButtons=True)
#6 Enact policy- display text about policy. Check if game should be over. Check if goverment has power to use and go to power used.
#7 Investigation then to 0
#8 Special election- double check logic goes back to regular rotation after
#9 Policy peek then to 0
#10 Execution then to 0- kill off player, double check logic and database are correctly updated, and turn rotation is kept.
#11 Victory screen

