function EventReceiver(websocket, poller, channels, last_msg, onmessage) {
    this.websocket_path = websocket;
    this.channels = channels;
    this.last_msg = last_msg;
    this.poller_base = poller;
    this.poller_path = poller + channels.join('|');
    if (onmessage)
        this.onmessage = onmessage;
    var receiver = this;

    function init_poll() {
        function long_poll() {
            $.ajax({
                url: receiver.poller_path,
                data: {last: receiver.last_msg},
                success: function (data, status, jqXHR) {
                    receiver.onmessage(data.message);
                    receiver.last_msg = data.id;
                    long_poll();
                },
                error: function (jqXHR, status, error) {
                    console.log('Long poll failure: ' + status);
                    console.log(jqXHR);
                    setTimeout(long_poll, 2000);
                },
                dataType: "json"
            });
        }
        long_poll();
    }

    if (window.WebSocket) {
        this.websocket = new WebSocket(websocket);
        var timeout = setTimeout(function () {
            receiver.websocket.close();
            receiver.websocket = null;
            init_poll();
        }, 2000);
        this.websocket.onopen = function (event) {
            clearTimeout(timeout);
            this.send(JSON.stringify({
                command: 'start-msg',
                start: last_msg
            }));
            this.send(JSON.stringify({
                command: 'set-filter',
                filter: channels
            }));
        };
        this.websocket.onmessage = function (event) {
            var data = JSON.parse(event.data);
            receiver.onmessage(data.message);
            receiver.last_msg = data.id;
        };
    } else {
        this.websocket = null;
        init_poll();
    }
}
