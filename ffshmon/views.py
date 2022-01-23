from ffshmon import app
from ffshmon.collectors import wireguard

@app.route("/")
def hello_world():
    
    return "<p>Wireguard status is </p>{}".format(wireguard.status())

@app.route("/health")
def health():
    health_status = None

    return wireguard.get_health()
