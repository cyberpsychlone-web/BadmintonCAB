####################################################################################################################################
#   Version Date            Name        Description
####################################################################################################################################
#   1.0     24-Jul-2025     S.K.Sami	WSGI implementation, Name change to the app
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
####################################################################################################################################



from app import app

if __name__ == "__main__":
    import threading, webbrowser

    def open_browser():
        webbrowser.open("http://127.0.0.1:5000")

    threading.Timer(1.0, open_browser).start()

    from waitress import serve
    serve(app, host="0.0.0.0", port=5000)