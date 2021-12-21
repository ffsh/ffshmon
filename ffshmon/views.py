from ffshmon import app
from ffshmon.collectors import wireguard

@app.route("/")
def hello_world():
    
    return "<p>Wireguard status is </p>{}".format(wireguard.status())

@app.route("/health")
def health():
    health_status = None

    wireguard_status = wireguard.status()

    if wireguard_status != "ok":
        health_status = wireguard_status


    if health_status == None:
        return "Health status is good."
    else:
        return "Health status is not good", 500