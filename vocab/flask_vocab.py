"""
Flask web site with vocabulary matching game
(identify vocabulary words that can be made 
from a scrambled string)
"""

# docker build -t myflask .
# docker run -p 5000:5000 myflask
# http://127.0.0.1:5000

import flask
import logging

# Our own modules
from letterbag import LetterBag
from vocab import Vocab # reads in a file of words (given to letter bag)
from jumble import jumbled # uses letterbag to create random string for user to find words
import config

###
# Globals
###
app = flask.Flask(__name__) # creates flask object 

CONFIG = config.configuration()
app.secret_key = CONFIG.SECRET_KEY  # Should allow using session variables

# One shared 'Vocab' object, read-only after initialization,
# shared by all threads and instances.  Otherwise we would have to
# store it in the browser and transmit it on each request/response cycle,
# or else read it from the file on each request/responce cycle,
# neither of which would be suitable for responding keystroke by keystroke.

WORDS = Vocab(CONFIG.VOCAB) # refer to vocab.py class

@app.route("/")
@app.route("/index")
def index(): # session refers to variables
    """The main page of the application"""
    flask.g.vocab = WORDS.as_list() # method returns a list of words
    flask.session["target_count"] = min(
        len(flask.g.vocab), CONFIG.SUCCESS_AT_COUNT)
    flask.session["jumble"] = jumbled(
        flask.g.vocab, flask.session["target_count"]) # creates a jumble of letters from word list
    flask.session["matches"] = [] # this is where any word matches made from jumble will go
    app.logger.debug("Session variables have been set")
    assert flask.session["matches"] == []
    assert flask.session["target_count"] > 0
    app.logger.debug("At least one seems to be set correctly")
    return flask.render_template('vocab.html')


@app.route("/keep_going")
def keep_going():
    """
    After initial use of index, we keep the same scrambled
    word and try to get more matches
    """
    flask.g.vocab = WORDS.as_list()
    return flask.render_template('vocab.html')


@app.route("/success")
def success():
    return flask.render_template('success.html') # redirects to a new page with link to start over

#######################
# Form handler.
# CIS 322 note:
#   You'll need to change this to a
#   a JSON request handler
#######################


@app.route("/_check")
def check():
    """
    User has submitted the form with a word ('attempt')
    that should be formed from the jumble and on the
    vocabulary list.  We respond depending on whether
    the word is on the vocab list (therefore correctly spelled),
    made only from the jumble letters, and not a word they
    already found.
    """
    app.logger.debug("Entering check")

    # The data we need, from form and from cookie
    text = flask.request.args.get("text", type=str) #text = flask.request.form["attempt"]
    jumble = flask.session["jumble"]
    matches = flask.session.get("matches", [])  # Default to empty list

    in_jumble = LetterBag(jumble).contains(text) # if jumble contains word
    matched = WORDS.has(text) # if in word list

    if matched and in_jumble and not (text in matches): # found new word
        matches.append(text) # add word to matches list
        text = ' '.join(matches)
        flask.session["matches"] = matches # update session
        result = {"message":"match found", "response": text} # or maybe do flask.session["matches"]
        app.logger.debug("Matches are " + text)

    elif text in matches: # if already found
        text = "You already found {}".format(text)
        result = {"message":"already found", "response": text}
        app.logger.debug("Already found " + text)

    elif not matched: # not in word list
        text = "{} isn't in the list of words".format(text)
        result = {"message":"not in list", "response": text}
        app.logger.debug("Not in list " + text)

    elif not in_jumble: # cant be made from jumble
        text = '"{}" can\'t be made from the letters {}'.format(text, jumble)
        result = {"message":"cant be made", "response": text}
        app.logger.debug("Cannot " + text)

    else:
        app.logger.debug("This case shouldn't happen!")
        assert False  # Raises AssertionError

    if len(matches) >= flask.session["target_count"]:
       success = "/success"
       result = {"message":"success", "response": success}

    app.logger.debug("Result is {}".format(result))
    return flask.jsonify(result=result)
    # this sends what ever was calculated to be rsval to html where javascript 
    # will return the correct value based off of what the value contains?

###############
# AJAX request handlers
#   These return JSON, rather than rendering pages.
###############


@app.route("/_example")
def example():
    """
    Example ajax request handler
    """
    app.logger.debug("Got a JSON request")
    rslt = {"key": "value"}
    return flask.jsonify(result=rslt)


#################
# Functions used within the templates
#################

@app.template_filter('filt')
def format_filt(something):
    """
    Example of a filter that can be used within
    the Jinja2 code
    """
    return "Not what you asked for"

###################
#   Error handlers
###################


@app.errorhandler(404)
def error_404(e):
    app.logger.warning("++ 404 error: {}".format(e))
    return flask.render_template('404.html'), 404


@app.errorhandler(500)
def error_500(e):
    app.logger.warning("++ 500 error: {}".format(e))
    assert not True  # I want to invoke the debugger
    return flask.render_template('500.html'), 500


@app.errorhandler(403)
def error_403(e):
    app.logger.warning("++ 403 error: {}".format(e))
    return flask.render_template('403.html'), 403


####

if __name__ == "__main__":
    if CONFIG.DEBUG:
        app.debug = True
        app.logger.setLevel(logging.DEBUG)
        app.logger.info(
            "Opening for global access on port {}".format(CONFIG.PORT))
        app.run(port=CONFIG.PORT, host="0.0.0.0")
