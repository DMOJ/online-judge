function urlSafeBase64Decode(text) {
    return Uint8Array.from([...atob(text.replace(/_/g, '/').replace(/-/g, '+'))], x => x.charCodeAt(0));
}

function urlSafeBase64Encode(buffer) {
    return btoa(String.fromCharCode(...new Uint8Array(buffer)))
        .replace(/\//g, '_')
        .replace(/\+/g, '-')
        .replace(/=+/g, '');
}

function decodeJSONBytes(object) {
    for (const key in object) {
        if (object.hasOwnProperty(key)) {
            const value = object[key];
            if (Array.isArray(value)) {
                value.forEach((element, index, array) => {
                    if (element._bytes) {
                        array[index] = urlSafeBase64Decode(element._bytes);
                    } else if (typeof value === 'object') {
                        decodeJSONBytes(value);
                    }
                });
            } else if (value._bytes) {
                object[key] = urlSafeBase64Decode(value._bytes);
            } else if (typeof value === 'object') {
                decodeJSONBytes(value);
            }
        }
    }
}
