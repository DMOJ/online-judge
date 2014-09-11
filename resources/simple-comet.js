window['SimpleComet'] = function() {
    var queue = [];

    var jsonp_cb = '_JSONP_comet_cb',
        min_delay = 100, timeout = 30000, since = 0, seq = 0;

    function create_jsonp_node(url) {
        var node = document.createElement('script');
        node.setAttribute('src', url);
        document.body.appendChild(node);

        return node;
    }

    function online_subscribe(url, cb, client_id) {
        var _url = url + '?since=' + encodeURIComponent(since) +
            '&t=' + (new Date).getTime() + '.' + seq++;
        client_id && (_url += '&client_id=' + encodeURIComponent(client_id));
        var jsonp_node = create_jsonp_node(_url);
        var cancel_timer = setTimeout(function() {
            jsonp_node.parentNode.removeChild(jsonp_node);
            online_subscribe(url, cb, client_id);
        }, timeout);
        window[jsonp_cb] = function(resp) {
            if (resp['return_code'] <= 0) {
                return;
            }
            clearTimeout(cancel_timer);
            jsonp_node.setAttribute('src', null);
            jsonp_node.parentNode &&
                jsonp_node.parentNode.removeChild(jsonp_node);
            if (resp.since < since) {
                return;
            }
            cb(resp);
            since = resp.last_id;
            setTimeout(function() {
                online_subscribe(url, cb, client_id);
            }, min_delay);
        }
    }

    function comet_ready_cb() {
        this.subscribe = online_subscribe;
        for (var args; args = queue.shift();) {
            this.subscribe.apply(this, args);
        }
    }

    function subscribe(url, cb, client_id) {
        queue.push(arguments);
    }

    function start() {
        setTimeout(comet_ready_cb, 1);
    }

    function since(time) {
        since = time;
    }

    return {
        'start': start,
        'min_delay': min_delay,
        'timeout': timeout,
        'subscribe': subscribe,
        'since': since
    };
}();
